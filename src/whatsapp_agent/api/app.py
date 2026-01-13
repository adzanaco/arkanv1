"""FastAPI application factory."""

from contextlib import asynccontextmanager
from fastapi import FastAPI

from whatsapp_agent.db import init_pool, close_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - initialize and cleanup resources."""
    # Startup
    await init_pool()
    yield
    # Shutdown
    await close_pool()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="WhatsApp Agent",
        description="LangGraph-powered WhatsApp automation agent",
        version="0.1.0",
        lifespan=lifespan,
    )
    
    # Import and include routers
    from whatsapp_agent.api.routes_evolution import router as evolution_router
    from whatsapp_agent.api.routes_health import router as health_router
    
    app.include_router(health_router)
    app.include_router(evolution_router)
    
    return app
