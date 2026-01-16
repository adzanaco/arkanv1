"""Message repository - database operations for inbound/outbound messages."""

from datetime import datetime

import psycopg

from whatsapp_agent.db.conn import get_conn


async def insert_inbound_message(
    chat_id: str,
    message_id: str,
    text: str,
    is_from_me: bool = False,
) -> bool:
    """
    Insert an inbound message. Returns True if inserted, False if duplicate.
    Uses ON CONFLICT DO NOTHING for idempotency.

    Args:
        chat_id: The WhatsApp chat ID
        message_id: The Evolution message ID (for dedupe)
        text: The message content
        is_from_me: True if sent by operator, False if from user
    """
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO inbound_messages (chat_id, message_id, text, is_from_me)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (message_id) DO NOTHING
                RETURNING id
                """,
                (chat_id, message_id, text, is_from_me),
            )
            result = await cur.fetchone()
            await conn.commit()
            return result is not None


async def get_last_message_time(chat_id: str) -> datetime | None:
    """Get the timestamp of the most recent inbound message for a chat."""
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT received_at FROM inbound_messages
                WHERE chat_id = %s
                ORDER BY received_at DESC
                LIMIT 1
                """,
                (chat_id,),
            )
            row = await cur.fetchone()
            return row[0] if row else None


async def fetch_unprocessed_messages(chat_id: str) -> list[tuple[int, str, datetime, bool]]:
    """
    Fetch all unprocessed messages for a chat, ordered by received_at.
    Returns list of (id, text, received_at, is_from_me) tuples.
    """
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, text, received_at, is_from_me FROM inbound_messages
                WHERE chat_id = %s AND processed_at IS NULL
                ORDER BY received_at ASC
                """,
                (chat_id,),
            )
            return await cur.fetchall()


async def mark_messages_processed(message_ids: list[int]) -> None:
    """Mark messages as processed by setting processed_at timestamp."""
    if not message_ids:
        return
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE inbound_messages
                SET processed_at = NOW()
                WHERE id = ANY(%s)
                """,
                (message_ids,),
            )
            await conn.commit()


async def insert_outbound_message(chat_id: str, text: str) -> int:
    """Log an outbound message. Returns the message ID."""
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO outbound_messages (chat_id, text)
                VALUES (%s, %s)
                RETURNING id
                """,
                (chat_id, text),
            )
            result = await cur.fetchone()
            await conn.commit()
            return result[0]
