# WhatsApp LangGraph Agent

## Quick Reference

| Command | Purpose |
|---------|---------|
| `pip install -e ".[dev]"` | Install deps |
| `uvicorn whatsapp_agent.api.app:create_app --factory --reload` | Run locally |
| `modal deploy modal_app.py` | Deploy to Modal |
| `psql $DATABASE_URL -f src/whatsapp_agent/db/schema.sql` | Init DB |

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
                          LangGraph Agent (GPT-5.2)
                                    ↓
                    ┌───────────────┼───────────────┐
                    ↓               ↓               ↓
              Typing Indicator  Send Reply   Mark Processed
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
    │   └── graph.py        # LangGraph StateGraph
    ├── integrations/
    │   ├── evolution_client.py   # send_text, set_typing
    │   └── evolution_normalize.py # Webhook → IncomingMessage
    └── workers/
        └── process_chat.py # Debounce + orchestration
```

## Stack

| Component | Technology |
|-----------|------------|
| LLM | OpenRouter `openai/gpt-5.2` |
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
- Webhook dedupe: unique constraint on `message_id`

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Postgres connection string |
| `OPENROUTER_API_KEY` | OpenRouter API key |
| `OPENROUTER_MODEL` | Model name (default: `openai/gpt-5.2`) |
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

