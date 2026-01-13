# WhatsApp LangGraph Agent

Auto-reply WhatsApp bot using LangGraph + Evolution API + Modal.

## Quick Start

### 1. Install dependencies

```bash
cd /Users/raedshuaibwork/Documents/Antigravity/arkanv1
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your credentials:
# - DATABASE_URL (Postgres - Neon/Supabase)
# - OPENROUTER_API_KEY
# - EVOLUTION_API_URL, EVOLUTION_API_KEY, EVOLUTION_INSTANCE
```

### 3. Initialize database

```bash
psql $DATABASE_URL -f src/whatsapp_agent/db/schema.sql
```

### 4. Run locally

```bash
uvicorn whatsapp_agent.api.app:create_app --factory --reload --port 8000
```

### 5. Expose webhook (new terminal)

```bash
ngrok http 8000
```

### 6. Configure Evolution webhook

Set webhook URL in Evolution API dashboard:
```
https://<ngrok-url>/webhooks/evolution
```

## Deploy to Modal

### 1. Create Modal secrets

```bash
modal secret create whatsapp-agent-secrets \
  DATABASE_URL="postgresql://..." \
  OPENROUTER_API_KEY="sk-or-..." \
  OPENROUTER_MODEL="openai/gpt-5.2" \
  EVOLUTION_API_URL="https://..." \
  EVOLUTION_API_KEY="..." \
  EVOLUTION_INSTANCE="..." \
  DEBOUNCE_SECONDS="10"
```

### 2. Deploy

```bash
modal deploy modal_app.py
```

### 3. Update Evolution webhook

Point to your Modal URL: `https://<app-name>--fastapi-app.modal.run/webhooks/evolution`

## Architecture

```
WhatsApp → Evolution → Webhook → Postgres → Worker → LangGraph → Reply
                                    ↓
                            10s debounce
                            Advisory lock
                            Typing indicator
```

## Key Features

- **10s debounce**: Waits for user to finish typing
- **Message batching**: Combines rapid messages into one
- **Typing indicator**: Shows "typing..." while processing
- **Persistent memory**: Postgres checkpointer per chat
- **Concurrency safe**: Advisory locks per chat
