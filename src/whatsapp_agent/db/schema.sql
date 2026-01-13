-- WhatsApp Agent Database Schema
-- Run: psql $DATABASE_URL -f src/whatsapp_agent/db/schema.sql

-- Inbound messages from WhatsApp
CREATE TABLE IF NOT EXISTS inbound_messages (
    id BIGSERIAL PRIMARY KEY,
    chat_id TEXT NOT NULL,
    message_id TEXT NOT NULL UNIQUE,  -- Evolution message ID for dedupe
    text TEXT NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ  -- NULL = not yet processed
);

-- Index for fetching unprocessed messages by chat
CREATE INDEX IF NOT EXISTS idx_inbound_chat_unprocessed 
ON inbound_messages (chat_id, received_at) 
WHERE processed_at IS NULL;

-- Index for debounce check (latest message time per chat)
CREATE INDEX IF NOT EXISTS idx_inbound_chat_received 
ON inbound_messages (chat_id, received_at DESC);

-- Outbound messages (for audit/logging)
CREATE TABLE IF NOT EXISTS outbound_messages (
    id BIGSERIAL PRIMARY KEY,
    chat_id TEXT NOT NULL,
    text TEXT NOT NULL,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_outbound_chat 
ON outbound_messages (chat_id, sent_at DESC);
