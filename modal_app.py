"""Modal deployment entrypoints."""

import modal

# Create the Modal app
app = modal.App("whatsapp-agent")

# Define the image with dependencies
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "langgraph>=0.2.0",
        "langchain-openai>=0.2.0",
        "langchain-core>=0.3.0",
        "langgraph-checkpoint-postgres>=2.0.0",
        "fastapi>=0.115.0",
        "uvicorn[standard]>=0.32.0",
        "httpx>=0.28.0",
        "psycopg[binary]>=3.2.0",
        "psycopg-pool>=3.2.0",
        "pydantic-settings>=2.6.0",
        "langsmith>=0.1.0",
    )
    .add_local_dir("src/whatsapp_agent", "/root/whatsapp_agent")
)

# Create a secret for environment variables
# Configure in Modal dashboard: modal secret create whatsapp-agent-secrets
secrets = modal.Secret.from_name("whatsapp-agent-secrets")


@app.function(
    image=image,
    secrets=[secrets],
    scaledown_window=300,
)
@modal.concurrent(max_inputs=100)
@modal.asgi_app()
def fastapi_app():
    """Serve the FastAPI application."""
    import sys
    sys.path.insert(0, "/root")
    
    from whatsapp_agent.api.app import create_app
    return create_app()


@app.function(
    image=image,
    secrets=[secrets],
    timeout=120,
)
async def process_chat_modal(chat_id: str):
    """
    Modal function for processing a chat.
    Can be spawned from the webhook handler for true async processing.
    """
    import sys
    sys.path.insert(0, "/root")
    
    from whatsapp_agent.db import init_pool, close_pool
    from whatsapp_agent.workers.process_chat import process_chat_task
    
    await init_pool()
    try:
        await process_chat_task(chat_id)
    finally:
        await close_pool()


# For local development, you can run:
# modal serve modal_app.py
# 
# For deployment:
# modal deploy modal_app.py
