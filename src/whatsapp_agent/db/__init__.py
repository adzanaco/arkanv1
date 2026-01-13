"""Database module - connection pool, repositories, and locks."""

from whatsapp_agent.db.conn import init_pool, close_pool, get_pool, get_conn
from whatsapp_agent.db.repo_messages import (
    insert_inbound_message,
    get_last_message_time,
    fetch_unprocessed_messages,
    mark_messages_processed,
    insert_outbound_message,
)
from whatsapp_agent.db.locks import advisory_lock, try_advisory_lock, release_advisory_lock

__all__ = [
    "init_pool",
    "close_pool",
    "get_pool",
    "get_conn",
    "insert_inbound_message",
    "get_last_message_time",
    "fetch_unprocessed_messages",
    "mark_messages_processed",
    "insert_outbound_message",
    "advisory_lock",
    "try_advisory_lock",
    "release_advisory_lock",
]
