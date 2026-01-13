"""LangGraph state definition for WhatsApp bot."""

from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class ChatState(TypedDict):
    """
    State for the WhatsApp chat agent.
    
    - messages: Conversation history, using add_messages reducer to append
    - user_id: The WhatsApp chat_id / phone number
    """
    messages: Annotated[list, add_messages]
    user_id: str
