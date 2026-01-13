"""Evolution API webhook routes."""

import logging
from fastapi import APIRouter, Request, BackgroundTasks

from whatsapp_agent.db import insert_inbound_message
from whatsapp_agent.integrations import normalize_webhook_payload
from whatsapp_agent.workers.process_chat import process_chat_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/evolution")
async def evolution_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receive webhook events from Evolution API.
    
    - Normalizes the payload
    - Inserts message to DB (with dedupe)
    - Triggers background processing
    """
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        return {"ok": False, "error": "Invalid JSON"}
    
    # Normalize the webhook payload
    message = normalize_webhook_payload(payload)
    
    if message is None:
        # Not a message we care about (status update, outgoing, etc.)
        return {"ok": True, "action": "ignored"}
    
    logger.info(f"Received message from {message.chat_id}: {message.text[:50]}...")
    
    # Insert to DB (dedupe by message_id)
    inserted = await insert_inbound_message(
        chat_id=message.chat_id,
        message_id=message.message_id,
        text=message.text,
    )
    
    if not inserted:
        # Duplicate message (webhook retry)
        logger.info(f"Duplicate message ignored: {message.message_id}")
        return {"ok": True, "action": "duplicate"}
    
    # Trigger background processing
    background_tasks.add_task(process_chat_task, message.chat_id)
    
    return {"ok": True, "action": "queued"}
