"""Normalize Evolution API webhook payloads."""

from dataclasses import dataclass
from typing import Any


@dataclass
class IncomingMessage:
    """Normalized inbound message from Evolution webhook."""
    message_id: str
    chat_id: str
    sender: str
    text: str
    is_group: bool
    timestamp: int
    from_me: bool  # True if sent by operator (account owner), False if from user


def normalize_webhook_payload(payload: dict[str, Any]) -> IncomingMessage | None:
    """
    Normalize an Evolution API webhook payload into an IncomingMessage.

    Returns None if the payload is not a valid message
    (e.g., status updates, empty messages, etc.)

    Note: We now capture BOTH user messages AND operator messages (fromMe=True)
    to provide full context to the AI.
    """
    # Check event type - we only want messages
    event = payload.get("event")
    if event != "messages.upsert":
        return None

    data = payload.get("data", {})

    # Check if this is a message we sent (operator message)
    key = data.get("key", {})
    from_me = key.get("fromMe", False)

    # Extract message content
    message = data.get("message", {})
    
    # Try different message types for text content
    text = (
        message.get("conversation") or
        message.get("extendedTextMessage", {}).get("text") or
        message.get("imageMessage", {}).get("caption") or
        message.get("videoMessage", {}).get("caption") or
        ""
    )
    
    # Skip empty messages
    if not text.strip():
        return None
    
    chat_id = key.get("remoteJid", "")
    is_group = chat_id.endswith("@g.us")
    
    # For groups, sender is in participant field; for DMs it's the chat_id
    sender = key.get("participant", chat_id) if is_group else chat_id
    
    return IncomingMessage(
        message_id=key.get("id", ""),
        chat_id=chat_id,
        sender=sender,
        text=text.strip(),
        is_group=is_group,
        timestamp=data.get("messageTimestamp", 0),
        from_me=from_me,
    )
