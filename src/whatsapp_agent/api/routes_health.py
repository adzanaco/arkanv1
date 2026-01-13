"""Health check routes."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@router.get("/")
async def root():
    """Root endpoint."""
    return {"service": "whatsapp-agent", "status": "running"}
