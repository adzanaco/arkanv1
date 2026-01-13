"""Evolution API client for sending messages and typing indicators."""

import httpx

from whatsapp_agent.settings import settings


class EvolutionClient:
    """Async client for Evolution API."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        instance: str | None = None,
    ):
        self.base_url = (base_url or settings.evolution_api_url).rstrip("/")
        self.api_key = api_key or settings.evolution_api_key
        self.instance = instance or settings.evolution_instance
        self._headers = {"apikey": self.api_key}

    async def send_text(self, to: str, text: str) -> dict:
        """
        Send a text message to a WhatsApp number/chat.
        
        Args:
            to: The recipient (phone@c.us or group JID)
            text: The message text
            
        Returns:
            Evolution API response
        """
        url = f"{self.base_url}/message/sendText/{self.instance}"
        payload = {
            "number": to,
            "text": text,
        }
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload, headers=self._headers)
            response.raise_for_status()
            return response.json()

    async def set_typing(self, to: str, duration: int = 3000) -> dict:
        """
        Show typing indicator in a chat.
        
        Args:
            to: The recipient (phone@c.us or group JID)
            duration: How long to show typing (ms), default 3000
            
        Returns:
            Evolution API response
        """
        url = f"{self.base_url}/chat/presence/{self.instance}"
        payload = {
            "number": to,
            "presence": "composing",
            "delay": duration,
        }
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload, headers=self._headers)
            response.raise_for_status()
            return response.json()

    async def mark_read(self, to: str, message_id: str) -> dict:
        """
        Mark a message as read.
        
        Args:
            to: The chat JID
            message_id: The message ID to mark as read
            
        Returns:
            Evolution API response
        """
        url = f"{self.base_url}/chat/markMessageAsRead/{self.instance}"
        payload = {
            "readMessages": [
                {
                    "remoteJid": to,
                    "id": message_id,
                }
            ]
        }
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload, headers=self._headers)
            response.raise_for_status()
            return response.json()


# Default client instance
evolution_client = EvolutionClient()
