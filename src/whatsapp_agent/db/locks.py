"""Postgres advisory locks for per-chat serialization."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
import hashlib

import psycopg

from whatsapp_agent.db.conn import get_conn


def _chat_id_to_lock_key(chat_id: str) -> int:
    """Convert chat_id string to a 64-bit integer for pg_advisory_lock."""
    # Use first 8 bytes of MD5 hash as lock key
    hash_bytes = hashlib.md5(chat_id.encode()).digest()[:8]
    return int.from_bytes(hash_bytes, byteorder="big", signed=True)


@asynccontextmanager
async def advisory_lock(chat_id: str) -> AsyncGenerator[None, None]:
    """
    Acquire an advisory lock for the given chat_id.
    Only one worker can hold the lock at a time.
    Lock is released when the context exits.
    """
    lock_key = _chat_id_to_lock_key(chat_id)
    
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            # Acquire lock (blocks until available)
            await cur.execute("SELECT pg_advisory_lock(%s)", (lock_key,))
            try:
                yield
            finally:
                # Release lock
                await cur.execute("SELECT pg_advisory_unlock(%s)", (lock_key,))


async def try_advisory_lock(chat_id: str) -> bool:
    """
    Try to acquire an advisory lock without blocking.
    Returns True if lock acquired, False if already held by another session.
    NOTE: Caller must manually release with release_advisory_lock().
    """
    lock_key = _chat_id_to_lock_key(chat_id)
    
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT pg_try_advisory_lock(%s)", (lock_key,))
            result = await cur.fetchone()
            return result[0] if result else False


async def release_advisory_lock(chat_id: str) -> None:
    """Release an advisory lock that was acquired with try_advisory_lock()."""
    lock_key = _chat_id_to_lock_key(chat_id)
    
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT pg_advisory_unlock(%s)", (lock_key,))
