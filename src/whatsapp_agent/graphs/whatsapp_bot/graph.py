"""LangGraph agent for WhatsApp bot."""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import trim_messages
import psycopg

from whatsapp_agent.settings import settings
from whatsapp_agent.graphs.whatsapp_bot.state import ChatState
from whatsapp_agent.graphs.whatsapp_bot.prompts import SYSTEM_PROMPT


def get_llm() -> ChatOpenAI:
    """Create the LLM instance configured for OpenRouter."""
    return ChatOpenAI(
        model=settings.openrouter_model,
        temperature=0.7,
        openai_api_key=settings.openrouter_api_key,
        openai_api_base="https://openrouter.ai/api/v1",
    )


async def agent_node(state: ChatState) -> dict:
    """
    Main agent node - processes messages and generates response.
    Limits history to last 20 messages to manage context window and cost.
    """
    llm = get_llm()

    # Trim messages to keep last 20 (plus system prompt implicitly via graph structure if managed there,
    # but here we pass SYSTEM_PROMPT explicitly in invoke)
    # We trim the state messages first
    trimmed_messages = trim_messages(
        state["messages"],
        strategy="last",
        token_counter=len, # Simple count-based trimming
        max_tokens=20,     # Keep last 20 messages
        start_on="human",  # Ensure we don't cut in middle of AI response (though less critical with simple list)
        include_system=False, # We manually add system prompt
        allow_partial=False,
    )

    response = await llm.ainvoke([SYSTEM_PROMPT, *trimmed_messages])
    return {"messages": [response]}


def build_graph() -> StateGraph:
    """Build the LangGraph state graph (not compiled)."""
    graph = StateGraph(ChatState)
    graph.add_node("agent", agent_node)
    graph.set_entry_point("agent")
    graph.add_edge("agent", END)
    return graph


async def create_checkpointer():
    """Create an async Postgres checkpointer for conversation memory."""
    conn = await psycopg.AsyncConnection.connect(settings.database_url, autocommit=True)
    checkpointer = AsyncPostgresSaver(conn)
    await checkpointer.setup()
    return checkpointer


async def build_app(checkpointer: AsyncPostgresSaver):
    """Build and compile the graph with a checkpointer."""
    graph = build_graph()
    return graph.compile(checkpointer=checkpointer)
