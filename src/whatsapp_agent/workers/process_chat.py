"""Background worker for processing chat messages with debounce."""

import asyncio
import logging
import random
from datetime import datetime, timezone

from langchain_core.messages import HumanMessage, AIMessage

from whatsapp_agent.settings import settings
from whatsapp_agent.db import (
    advisory_lock,
    get_last_message_time,
    fetch_unprocessed_messages,
    mark_messages_processed,
    insert_outbound_message,
)
from whatsapp_agent.graphs.whatsapp_bot import build_app, create_checkpointer
from whatsapp_agent.integrations import evolution_client

logger = logging.getLogger(__name__)

# Typing indicator settings
TYPING_MS_PER_CHAR = 50
MIN_TYPING_MS = 2000
MAX_TYPING_MS = 60000

# Cache the compiled graph app
_graph_app = None
_checkpointer = None


async def get_graph_app():
    """Get or create the compiled graph app."""
    global _graph_app, _checkpointer
    if _graph_app is None:
        _checkpointer = await create_checkpointer()
        _graph_app = await build_app(_checkpointer)
    return _graph_app


async def process_chat_task(chat_id: str) -> None:
    """
    Process a chat with debounce logic.

    1. Acquire advisory lock for chat_id
    2. Wait until no new messages for DEBOUNCE_SECONDS
    3. Fetch all unprocessed messages (user + operator)
    4. Inject operator messages as AIMessage into LangGraph state
    5. If last message is from user, run AI agent and send reply
    6. If last message is from operator, skip AI (operator is handling it)
    """
    logger.info(f"Starting chat processing for {chat_id}")

    try:
        async with advisory_lock(chat_id):
            # Debounce loop - wait for typing to stop
            while True:
                last_message_time = await get_last_message_time(chat_id)
                if last_message_time is None:
                    logger.warning(f"No messages found for {chat_id}")
                    return

                now = datetime.now(timezone.utc)
                elapsed = (now - last_message_time).total_seconds()
                remaining = settings.debounce_seconds - elapsed

                if remaining <= 0:
                    break

                logger.debug(f"Waiting {remaining:.1f}s for debounce on {chat_id}")
                await asyncio.sleep(remaining)

            # Fetch all unprocessed messages (now includes is_from_me)
            messages = await fetch_unprocessed_messages(chat_id)
            if not messages:
                logger.info(f"No unprocessed messages for {chat_id}")
                return

            # Separate messages: (id, text, received_at, is_from_me)
            message_ids = [m[0] for m in messages]
            last_is_from_me = messages[-1][3]  # Check if last message is from operator

            logger.info(f"Processing {len(messages)} messages for {chat_id}, last_is_from_me={last_is_from_me}")

            # Setup LangGraph
            graph_app = await get_graph_app()
            thread_id = f"wa:{chat_id}"
            config = {"configurable": {"thread_id": thread_id}}

            # Separate operator and user messages
            operator_texts = [m[1] for m in messages if m[3]]  # is_from_me = True
            user_texts = [m[1] for m in messages if not m[3]]  # is_from_me = False

            # Inject operator messages as AIMessage (they speak as the assistant)
            if operator_texts:
                combined_operator = "\n".join(operator_texts)
                logger.info(f"Injecting operator message(s) into state: {combined_operator[:50]}...")
                await graph_app.aupdate_state(
                    config,
                    {"messages": [AIMessage(content=combined_operator)]},
                )

            # If last message is from operator, skip AI generation
            if last_is_from_me:
                logger.info(f"Last message is from operator - skipping AI generation for {chat_id}")
                await mark_messages_processed(message_ids)
                return

            # User messages exist and last is from user - run AI
            if not user_texts:
                logger.info(f"No user messages to process for {chat_id}")
                await mark_messages_processed(message_ids)
                return

            combined_user = "\n".join(user_texts)
            logger.info(f"Running AI agent for {chat_id} with user input: {combined_user[:50]}...")

            result = await graph_app.ainvoke(
                {
                    "user_id": chat_id,
                    "messages": [HumanMessage(content=combined_user)],
                },
                config=config,
            )

            # Extract reply
            full_response = result["messages"][-1].content

            # Split messages by delimiter
            messages_to_send = [m.strip() for m in full_response.split("|||") if m.strip()]

            for i, reply_part in enumerate(messages_to_send):
                # Calculate typing duration for this part
                typing_duration = min(
                    max(len(reply_part) * TYPING_MS_PER_CHAR, MIN_TYPING_MS),
                    MAX_TYPING_MS
                )

                # Show typing indicator dynamically
                try:
                    # Pulse loop for typing indicator
                    logger.info(f"Typing part {i+1}/{len(messages_to_send)} for {typing_duration}ms based on {len(reply_part)} chars (pulsing)")
                    start_time = datetime.now(timezone.utc)

                    while (datetime.now(timezone.utc) - start_time).total_seconds() * 1000 < typing_duration:
                        # Refresh typing indicator (ask for 5s display)
                        await evolution_client.set_typing(chat_id, duration=5000)

                        # Wait for a "pulse" interval (e.g. 2.5s) or whatever is left
                        elapsed_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                        remaining = typing_duration - elapsed_ms
                        sleep_time = min(2500, remaining)

                        if sleep_time > 0:
                            await asyncio.sleep(sleep_time / 1000)
                except Exception as e:
                    logger.warning(f"Failed to set typing indicator: {e}")

                # Send reply part
                try:
                    await evolution_client.send_text(chat_id, reply_part)
                    await insert_outbound_message(chat_id, reply_part)
                    logger.info(f"Sent reply part {i+1} to {chat_id}: {reply_part[:50]}...")
                except Exception as e:
                    logger.error(f"Failed to send reply to {chat_id}: {e}")
                    raise

                # Human pause between messages (if not the last one)
                if i < len(messages_to_send) - 1:
                    pause_ms = random.uniform(500, 1500)
                    logger.info(f"Human pause for {pause_ms:.0f}ms")
                    await asyncio.sleep(pause_ms / 1000)

            # Mark messages as processed
            await mark_messages_processed(message_ids)

    except Exception as e:
        logger.exception(f"Error processing chat {chat_id}: {e}")
        raise
