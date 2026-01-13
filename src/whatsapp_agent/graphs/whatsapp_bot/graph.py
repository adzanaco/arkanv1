"""LangGraph agent for WhatsApp bot."""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_openai import ChatOpenAI

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
    """
    llm = get_llm()
    response = await llm.ainvoke([SYSTEM_PROMPT, *state["messages"]])
    return {"messages": [response]}


def build_graph() -> StateGraph:
    """Build the LangGraph state graph (not compiled)."""
    graph = StateGraph(ChatState)
    graph.add_node("agent", agent_node)
    graph.set_entry_point("agent")
    graph.add_edge("agent", END)
    return graph


async def create_checkpointer() -> AsyncPostgresSaver:
    """Create an async Postgres checkpointer for conversation memory."""
    checkpointer = AsyncPostgresSaver.from_conn_string(settings.database_url)
    await checkpointer.setup()
    return checkpointer


async def build_app(checkpointer: AsyncPostgresSaver):
    """Build and compile the graph with a checkpointer."""
    graph = build_graph()
    return graph.compile(checkpointer=checkpointer)
