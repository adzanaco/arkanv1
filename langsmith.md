# LangSmith Reference Guide

## What is LangSmith?

LangSmith is LangChain's observability platform for LLM applications. It's structured logging/tracing designed specifically for LangChain and LangGraph apps.

**Plain logging:** `print("LLM called")` → flat text in console

**LangSmith:** Captures the full execution tree:
```
Trace: WhatsApp message received
├── Node: fetch_messages (2ms)
├── Node: generate_reply
│   └── LLM Call: GPT-4.1 (1.2s, 450 tokens, $0.003)
│       ├── Input: [system prompt + messages]
│       └── Output: "hey! let me check that for you"
├── Node: send_reply (180ms)
└── Total: 1.4s
```

## Key Features

| Feature | Description |
|---------|-------------|
| **Tracing** | Captures every LLM call, tool execution, and state transition as a visual tree |
| **Debugging** | Step through agent runs, compare traces, see exactly what went wrong |
| **Evaluation** | Test prompts against datasets, run LLM-as-judge quality checks |
| **Cost Tracking** | Monitor token usage and API costs per trace |
| **Prompt Management** | Version and organize prompts via UI |

## Architecture & Data Flow

```
Your App (LangGraph/LangChain)
    → SDK captures spans/runs
    → Sends to LangSmith API
    → Stored as trace data
    → Viewable in LangSmith UI
```

**Data Model:**
- **Run/Span**: Individual execution unit (LLM call, tool call, chain step)
- **Trace**: Collection of related runs forming a request tree
- **Thread**: Groups of related traces (e.g., a conversation)
- **Feedback**: Human or automated quality annotations

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `LANGSMITH_TRACING` | Yes | Set to `true` to enable tracing |
| `LANGSMITH_API_KEY` | Yes | Your API key (starts with `ls_...`) |
| `LANGSMITH_PROJECT` | No | Project name to group traces (default: "default") |
| `LANGSMITH_ENDPOINT` | No | API endpoint (default: LangSmith cloud) |

**Legacy variables** (still work but `LANGSMITH_*` prefix is preferred):
- `LANGCHAIN_TRACING_V2` → use `LANGSMITH_TRACING`
- `LANGCHAIN_API_KEY` → use `LANGSMITH_API_KEY`

## Integration with LangGraph

LangGraph has **native, automatic integration**. No code changes needed - just set environment variables and LangGraph traces automatically flow to LangSmith.

What gets captured automatically:
- State transitions
- Node executions as individual spans
- LLM calls with inputs/outputs
- Tool executions
- Latency metrics

## Setup Instructions

### 1. Install the SDK

```bash
pip install langsmith
```

Or add to `pyproject.toml`:
```toml
dependencies = [
    # ... existing deps ...
    "langsmith>=0.1.0",
]
```

### 2. Get API Key

1. Go to https://smith.langchain.com/
2. Sign up / Log in
3. Go to Settings → API Keys
4. Create a new API key (starts with `ls_...`)

### 3. Set Environment Variables

**Local development (.env):**
```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls_your_key_here
LANGCHAIN_PROJECT=whatsapp-agent
```

**Modal deployment:**
```bash
/Users/raedshuaibwork/Library/Python/3.13/bin/modal secret create whatsapp-agent-secrets \
  DATABASE_URL="..." \
  OPENROUTER_API_KEY="..." \
  # ... existing secrets ... \
  LANGCHAIN_TRACING_V2="true" \
  LANGCHAIN_API_KEY="ls_your_key_here" \
  LANGCHAIN_PROJECT="whatsapp-agent"
```

### 4. No Code Changes Required

LangGraph will automatically trace to LangSmith when environment variables are set.

## Manual Tracing (Optional)

For custom functions outside LangGraph, use the `@traceable` decorator:

```python
from langsmith import traceable

@traceable
def my_custom_function(input_data):
    # This will appear as a span in your traces
    result = do_something(input_data)
    return result
```

For wrapping OpenAI clients directly:

```python
from langsmith import wrap_openai
import openai

client = wrap_openai(openai.Client())
# All calls through this client are now traced
```

## Pricing

| Tier | Price | Seats | Included Traces/mo |
|------|-------|-------|-------------------|
| **Developer** | $0 | 1 max | 5,000 |
| **Plus** | $39/seat/mo | Up to 10 | 10,000 |
| **Enterprise** | Custom | Unlimited | Custom |

**Overage pricing:**
- Base traces: $0.50 per 1,000 traces
- Extended traces (longer retention): $5.00 per 1,000 traces

## When to Use LangSmith

**Worth it when:**
- Debugging weird agent behavior
- A/B testing prompts
- Need cost breakdowns per conversation
- Scaling to production and need monitoring
- Multiple team members need visibility

**Skip it when:**
- Bot is working fine and you just need basic audit trail
- Your existing DB tables provide enough visibility
- You're cost-sensitive and don't need the features

## Useful Links

- **Dashboard**: https://smith.langchain.com/
- **Docs**: https://docs.smith.langchain.com/
- **Python SDK**: https://github.com/langchain-ai/langsmith-sdk
- **Pricing**: https://www.langchain.com/pricing

## Quick Reference Commands

```bash
# Check if tracing is enabled (Python)
python -c "import os; print(os.getenv('LANGSMITH_TRACING'))"

# View traces
# Go to https://smith.langchain.com/ → Select your project

# Test connection
python -c "from langsmith import Client; c = Client(); print(c.list_projects())"
```
