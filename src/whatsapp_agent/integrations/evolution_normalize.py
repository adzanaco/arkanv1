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


def normalize_webhook_payload(payload: dict[str, Any]) -> IncomingMessage | None:
    """
    Normalize an Evolution API webhook payload into an IncomingMessage.
    
    Returns None if the payload is not a valid incoming message
    (e.g., status updates, outgoing messages, etc.)
    """
    # Check event type - we only want incoming messages
    event = payload.get("event")
    if event != "messages.upsert":
        return None
    
    data = payload.get("data", {})
    
    # Skip if this is a message we sent (fromMe = True)
    key = data.get("key", {})
    if key.get("fromMe", False):
        return None
    
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
    )
