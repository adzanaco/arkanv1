"""Background worker for processing chat messages with debounce."""

import asyncio
import logging
from datetime import datetime, timezone

from langchain_core.messages import HumanMessage

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
    3. Combine all unprocessed messages
    4. Run LangGraph agent
    5. Send reply with typing indicator
    """
    logger.info(f"Starting chat processing for {chat_id}")
    
    try:
        async with advisory_lock(chat_id):
            # Debounce loop - wait for user to stop typing
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
            
            # Fetch all unprocessed messages
            messages = await fetch_unprocessed_messages(chat_id)
            if not messages:
                logger.info(f"No unprocessed messages for {chat_id}")
                return
            
            # Combine message texts
            message_ids = [m[0] for m in messages]
            combined_text = "\n".join(m[1] for m in messages)
            
            logger.info(f"Processing {len(messages)} messages for {chat_id}")
            
            # Show typing indicator
            try:
                await evolution_client.set_typing(chat_id, duration=5000)
            except Exception as e:
                logger.warning(f"Failed to set typing indicator: {e}")
            
            # Run LangGraph agent
            graph_app = await get_graph_app()
            thread_id = f"wa:{chat_id}"
            config = {"configurable": {"thread_id": thread_id}}
            
            result = await graph_app.ainvoke(
                {
                    "user_id": chat_id,
                    "messages": [HumanMessage(content=combined_text)],
                },
                config=config,
            )
            
            # Extract reply
            reply = result["messages"][-1].content
            
            # Send reply
            try:
                await evolution_client.send_text(chat_id, reply)
                await insert_outbound_message(chat_id, reply)
                logger.info(f"Sent reply to {chat_id}: {reply[:50]}...")
            except Exception as e:
                logger.error(f"Failed to send reply to {chat_id}: {e}")
                raise
            
            # Mark messages as processed
            await mark_messages_processed(message_ids)
            
    except Exception as e:
        logger.exception(f"Error processing chat {chat_id}: {e}")
        raise
