"""Integrations module - Evolution API client and helpers."""

from whatsapp_agent.integrations.evolution_client import EvolutionClient, evolution_client
from whatsapp_agent.integrations.evolution_normalize import (
    IncomingMessage,
    normalize_webhook_payload,
)

__all__ = [
    "EvolutionClient",
    "evolution_client",
    "IncomingMessage",
    "normalize_webhook_payload",
]
