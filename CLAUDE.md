# WhatsApp LangGraph Agent

## Deployment Status: LIVE

| Component | URL / Value |
|-----------|-------------|
| Modal App | https://adzanaco--whatsapp-agent-fastapi-app.modal.run |
| Webhook Endpoint | https://adzanaco--whatsapp-agent-fastapi-app.modal.run/webhooks/evolution |
| Modal Dashboard | https://modal.com/apps/adzanaco/main/deployed/whatsapp-agent |
| Evolution API | https://n8nmemory-evolution-api.vxpcvk.easypanel.host |
| Evolution Instance | `Raed Moral` (URL-encoded in code due to space) |
| Postgres | Hosted on Hetzner via Easypanel at `easypanel.adzana.ae:5430` |
| Database | `n8nmemory` |

## Quick Reference

| Command | Purpose |
|---------|---------|
| `pip install -e ".[dev]"` | Install deps |
| `uvicorn whatsapp_agent.api.app:create_app --factory --reload` | Run locally |
| `/Users/raedshuaibwork/Library/Python/3.13/bin/modal deploy modal_app.py` | Deploy to Modal |

## Current Configuration

Modal secrets are stored in `whatsapp-agent-secrets`:
- `DATABASE_URL` = `postgresql://postgres:****@easypanel.adzana.ae:5430/n8nmemory?sslmode=disable`
- `OPENROUTER_API_KEY` = configured
- `OPENROUTER_MODEL` = `openai/gpt-5.2`
- `EVOLUTION_API_URL` = `https://n8nmemory-evolution-api.vxpcvk.easypanel.host`
- `EVOLUTION_API_KEY` = configured
- `EVOLUTION_INSTANCE` = `Raed Moral`
- `DEBOUNCE_SECONDS` = `10`

## Architecture

```
WhatsApp → Evolution API → POST /webhooks/evolution
                                    ↓
                          FastAPI (normalize + dedupe + insert)
                                    ↓
                          Background Worker
                                    ↓
                    ┌───────────────┼───────────────┐
                    ↓               ↓               ↓
              Advisory Lock   Debounce 10s   Fetch Messages
                                    ↓
                          LangGraph Agent (GPT-4.1)
                                    ↓
                    ┌───────────────┼───────────────┐
                    ↓               ↓               ↓
              Generate Reply    Calc Time    Pulse Typing (Loop)
                    │               │               │
                    └───────────────┼───────────────┘
                                    ↓
                               Send Reply
                                    ↓
                              Mark Processed
```

## Project Structure

```
arkanv1/
├── pyproject.toml          # Dependencies
├── .env.example            # Env var template
├── modal_app.py            # Modal deployment
├── CLAUDE.md               # This file
├── README.md               # Setup instructions
└── src/whatsapp_agent/
    ├── settings.py         # Pydantic config
    ├── api/
    │   ├── app.py          # FastAPI factory
    │   ├── routes_evolution.py  # Webhook endpoint
    │   └── routes_health.py     # Health checks
    ├── db/
    │   ├── schema.sql      # Postgres tables
    │   ├── conn.py         # Connection pool
    │   ├── repo_messages.py # CRUD for messages
    │   └── locks.py        # Advisory locks
    ├── graphs/whatsapp_bot/
    │   ├── state.py        # ChatState TypedDict
    │   ├── prompts.py      # System prompt
    │   ├── graph.py        # LangGraph StateGraph
    ├── integrations/
    │   ├── evolution_client.py   # send_text, set_typing (URL-encodes instance name)
    │   └── evolution_normalize.py # Webhook → IncomingMessage
    └── workers/
        └── process_chat.py # Debounce + orchestration
```

## Stack

| Component | Technology |
|-----------|------------|
| LLM | OpenRouter `openai/gpt-4.1` |
| Orchestration | LangGraph + Postgres checkpointer |
| API | FastAPI |
| Database | Postgres (messages + checkpoints) |
| WhatsApp | Evolution API |
| Deploy | Modal |

## Key Conventions

- `thread_id = "wa:" + chat_id` for LangGraph memory
- All async code uses `async/await`
- Debounce: 10s wait after last message
- Advisory locks: one worker per chat at a time
- Context Limit: Last 20 messages (managed by `trim_messages` in `graph.py`)
- Webhook dedupe: unique constraint on `message_id`
- Instance name is URL-encoded in `evolution_client.py` (handles spaces)
- **Operator messages**: Captured via `is_from_me` flag, injected as `AIMessage` for context

## Operator Takeover

The system captures messages sent by the operator (account owner) from WhatsApp and includes them in the AI's context.

**How it works:**
- All messages (user AND operator) are stored in `inbound_messages` with `is_from_me` flag
- Operator messages (`is_from_me=true`) are injected into LangGraph as `AIMessage`
- If the **last message** in a batch is from the operator, the AI does NOT reply (operator is handling it)
- If the **last message** is from the user, AI replies normally (with operator messages as context)

**Behavior Table:**

| Scenario | AI Response |
|----------|-------------|
| User sends message | AI replies after 10s debounce |
| Operator sends message | Stored as context, AI stays silent |
| User → Operator | AI stays silent (operator took over) |
| Operator → User | AI replies (has operator's message as context) |

**Note:** There is no cooldown timer. The AI decision is purely based on who sent the last message in each batch.

## Persona & Behavior

- **Identity**: "Raed's Assistant" (Human-like, efficient, casual).
- **Style**: Lowercase, no start-of-sentence caps, no perfect punctuation.
- **Multi-Message**: The bot uses `|||` in the prompt to separate thoughts.
    - `process_chat.py` splits this delimiter to send sequential bubbles.
    - Includes dynamic typing indicators and random "human pauses" (0.5s-1.5s) between bubbles.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Postgres connection string |
| `OPENROUTER_API_KEY` | OpenRouter API key |
| `OPENROUTER_MODEL` | Model name (default: `openai/gpt-4.1`) |
| `EVOLUTION_API_URL` | Evolution API base URL |
| `EVOLUTION_API_KEY` | Evolution API key |
| `EVOLUTION_INSTANCE` | Evolution instance name |
| `DEBOUNCE_SECONDS` | Wait time (default: 10) |

## Extending the Agent

To add tools, edit `graphs/whatsapp_bot/graph.py`:
1. Define tools in a new `tools.py`
2. Bind tools to the LLM: `llm.bind_tools([...])`
3. Add a tool execution node
4. Add conditional edges for tool routing

## Useful Commands

```bash
# Update Modal secrets
/Users/raedshuaibwork/Library/Python/3.13/bin/modal secret create whatsapp-agent-secrets \
  DATABASE_URL="..." \
  OPENROUTER_API_KEY="..." \
  # ... etc

# Check Evolution API instances
curl -H "apikey: YOUR_KEY" https://n8nmemory-evolution-api.vxpcvk.easypanel.host/instance/fetchInstances

# Set Evolution webhook
curl -X POST "https://n8nmemory-evolution-api.vxpcvk.easypanel.host/webhook/set/Raed%20Moral" \
  -H "apikey: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"webhook":{"enabled":true,"url":"https://adzanaco--whatsapp-agent-fastapi-app.modal.run/webhooks/evolution","events":["MESSAGES_UPSERT"]}}'
```

## Troubleshooting

- **Instance name has space**: Already handled - `evolution_client.py` URL-encodes the instance name
- **Modal CLI not in PATH**: Use full path `/Users/raedshuaibwork/Library/Python/3.13/bin/modal`
- **Postgres connection**: Use `postgresql://` scheme (not `postgres://`) for psycopg3

## System Overview (The Story)

This system is a **WhatsApp Bot** that uses **Evolution API** to send/receive messages and **LangGraph (AI)** to decide what to say.

**The Flow:**
1.  **WhatsApp** sends a message → **Evolution API**
2.  **Evolution API** calls our **Webhook** (`routes_evolution.py`)
3.  **Webhook** saves message to **Postgres** and starts a **Background Worker** (`process_chat.py`)
4.  **Worker** locks the chat (so only one reply happens at a time), waits for typing to stop (Debounce), and calls the **AI Agent** (`graph.py`)
5.  **AI Agent** generates a response
6.  **Worker** sends the reply back via **Evolution API**

## File Map (Tag These for AI)

### ⚙️ Configuration & Setup
*   `src/whatsapp_agent/settings.py`: **The Config**. Reads environment variables (API keys, DB URLs). Check this if env vars aren't loading.
*   `modal_app.py`: **The Deployment**. Defines how the app runs on Modal (cloud). Edit this to change CPU/Memory or secrets.
*   `.env`: **Secrets**. Local API keys (not committed to Git).

### 🚪 The Front Desk (API)
*   `src/whatsapp_agent/api/app.py`: **The Server**. Main entry point. Sets up logging and database pool.
*   `src/whatsapp_agent/api/routes_evolution.py`: **The Webhook**. Receives JSON from Evolution API.
    *   *Role*: Sanity checks the data, saves it to DB, and triggers `process_chat_task`.

### 🗄️ The Inbox (Database)
*   `src/whatsapp_agent/db/schema.sql`: **The Tables**. Defines `inbound_messages` (with `is_from_me` flag) and `outbound_messages`.
*   `src/whatsapp_agent/db/conn.py`: **The Connection**. Manages the pool of connections to Postgres.
*   `src/whatsapp_agent/db/repo_messages.py`: **The Librarian**. Functions to `INSERT` messages or `SELECT` unprocessed ones.
*   `src/whatsapp_agent/db/locks.py`: **The Key**. Handles "Advisory Locks" to prevent race conditions.

### 👷 The Receptionist (Worker)
*   `src/whatsapp_agent/workers/process_chat.py`: **The Manager**.
    *   *Role*: This is the most complex file. It orchestrates everything:
        1.  Acquires Lock.
        2.  Loops to wait for "Debounce" (waiting for user to stop typing).
        3.  Fetches all unread messages (user + operator).
        4.  Injects operator messages as `AIMessage` into LangGraph state.
        5.  If last message is from user → calls the AI Graph → sends reply.
        6.  If last message is from operator → skips AI (operator is handling it).

### 🧠 The Brain (AI Agent)
*   `src/whatsapp_agent/graphs/whatsapp_bot/graph.py`: **The Logic**. Defines the LangGraph structure (Nodes and Edges).
*   `src/whatsapp_agent/graphs/whatsapp_bot/prompts.py`: **The Personality**. Contains the `SYSTEM_PROMPT` that tells the AI who it is.
*   `src/whatsapp_agent/graphs/whatsapp_bot/state.py`: **The Memory**. Defines the `ChatState` (what data acts as context).

### 🔌 The Connectors (Integrations)
*   `src/whatsapp_agent/integrations/evolution_client.py`: **The Messenger**. Python functions to call Evolution API (e.g., `send_text`, `set_typing`).
*   `src/whatsapp_agent/integrations/evolution_normalize.py`: **The Translator**. Converts complex Evolution API webhooks into a simple `IncomingMessage` object. Captures both user and operator messages via `from_me` flag.

## Common Tasks (How to Guide the AI)

*   **"Change the bot's behavior/personality"**: Edit `src/whatsapp_agent/graphs/whatsapp_bot/prompts.py`.
*   **"The bot is stuck/not replying"**: Check `src/whatsapp_agent/workers/process_chat.py` or `src/whatsapp_agent/db/locks.py`.
*   **"Add a new tool (like searching the web)"**:
    1.  Define tool in `src/whatsapp_agent/graphs/whatsapp_bot/tools.py` (create if missing).
    2.  Register it in `src/whatsapp_agent/graphs/whatsapp_bot/graph.py`.
*   **"Change how long it waits before replying"**: Change `DEBOUNCE_SECONDS` in `src/whatsapp_agent/settings.py` or `.env`.
*   **"AI should stop replying when I message manually"**: Already implemented - if operator sends last message, AI stays silent.
