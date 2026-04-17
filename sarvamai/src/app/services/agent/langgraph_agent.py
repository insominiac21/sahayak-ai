"""
Phase 3: LangGraph Agent for Sahayak AI
Handles multi-step reasoning with tools: scheme search, eligibility calc, web search
Uses Supabase Postgres checkpointer for persistent memory.
"""

import os
import logging
import itertools
from typing import Annotated, Any, Dict, List, TypedDict
from dotenv import load_dotenv

# Core LangGraph imports
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

# LangChain imports
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

# Qdrant & embedding
from qdrant_client import QdrantClient
from huggingface_hub import InferenceClient

# Existing Sahayak imports
from app.core.config import settings

load_dotenv()
logger = logging.getLogger(__name__)

# ============================================================================
# 1. GLOBAL CLIENTS
# ============================================================================

qdrant = QdrantClient(
    url=settings.QDRANT_URL, 
    api_key=settings.QDRANT_API_KEY
)

hf_client = InferenceClient(api_key=settings.HF_TOKEN)

# ============================================================================
# ROUND-ROBIN GEMINI API KEY MANAGEMENT
# ============================================================================
# Load all 6 Gemini keys into a list
API_KEYS = [
    settings.GEMINI_API_KEY1,
    settings.GEMINI_API_KEY2,
    settings.GEMINI_API_KEY3,
    settings.GEMINI_API_KEY4,
    settings.GEMINI_API_KEY5,
    settings.GEMINI_API_KEY6,
]

# Create an infinite cyclic iterator that rotates through all keys
gemini_key_cycle = itertools.cycle(API_KEYS)
logger.info(f"✅ Round-robin Gemini initialized with 6 API keys")

def get_next_gemini_llm():
    """
    Returns a ChatGoogleGenerativeAI instance using the next API key in the round-robin.
    This ensures automatic load distribution and fallback if one key hits rate limits.
    """
    next_key = next(gemini_key_cycle)
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        api_key=next_key,  # Explicitly override environment variable search
        temperature=0.7,
        max_tokens=500,
    )

# Initialize the first LLM instance for startup
llm = get_next_gemini_llm()

# Setup database checkpointer for conversation memory
# For now, use MemorySaver (development/testing)
# For production with Postgres, install langgraph-postgres and use PostgresSaver
checkpointer = MemorySaver()
logger.info("✅ MemorySaver checkpointer initialized (conversation memory enabled)")

# Future: Production PostgreSQL setup
# Uncomment when langgraph-postgres is available
# DB_URI = settings.SUPABASE_POSTGRES_URI
# if not DB_URI:
#     raise RuntimeError("SUPABASE_POSTGRES_URI not set in .env")
# try:
#     from langgraph_postgres import PostgresSaver as PGSaver
#     connection_pool = ConnectionPool(
#         conninfo=DB_URI,
#         max_size=10,
#         kwargs={"autocommit": True}
#     )
#     checkpointer = PGSaver(connection_pool)
#     checkpointer.setup()
#     logger.info("✅ PostgreSQL checkpointer initialized")
# except Exception as e:
#     logger.error(f"❌ Failed to setup PostgreSQL checkpointer: {e}, falling back to MemorySaver")
#     checkpointer = MemorySaver()

# ============================================================================
# 2. STATE DEFINITION
# ============================================================================

class AgentState(TypedDict):
    """State passed through the agent workflow"""
    messages: Annotated[List[BaseMessage], "Conversation history"]
    intent: str  # "scheme_search", "eligibility_check", "combined"
    user_context: Dict[str, Any]  # income, age, state, etc.


# ============================================================================
# 3. TOOLS DEFINITIONS
# ============================================================================

@tool
def search_schemes(query: str) -> str:
    """
    Search the government scheme vector database.
    Use this to find details about schemes like PMAY-U, PM-JAY, PMJDY, etc.
    
    Args:
        query: Search query about a scheme (e.g., "PMAY-U eligibility requirements")
    
    Returns:
        Relevant scheme info from Qdrant or error message
    """
    try:
        # Use HF embeddings (consistent with your system)
        query_embedding = hf_client.feature_extraction(
            text=query,
            model="BAAI/bge-m3"
        )
        
        # Validate embedding
        if not query_embedding or len(query_embedding) == 0:
            return "Error: Failed to generate query embedding"
        
        # Search Qdrant
        search_results = qdrant.search(
            collection_name="schemes",
            query_vector=query_embedding,
            limit=4
        )
        
        if not search_results:
            return "No relevant scheme information found in the database."
        
        # Format results
        context_parts = []
        for hit in search_results:
            scheme_name = hit.payload.get("scheme_name", "Unknown Scheme")
            text = hit.payload.get("text", "")[:300]  # Truncate to 300 chars
            score = hit.score
            context_parts.append(f"[{scheme_name} (relevance: {score:.2f})]\n{text}")
        
        return "\n\n---\n\n".join(context_parts)
        
    except Exception as e:
        logger.error(f"Error in search_schemes: {e}")
        return f"Error accessing scheme database: {str(e)}"


@tool
def check_eligibility(scheme: str, income: int, age: int = None, state: str = None) -> str:
    """
    Check eligibility for a specific scheme based on income and demographics.
    
    Args:
        scheme: Scheme name (e.g., "PMAY-U", "PM-JAY", "PMJDY")
        income: Annual income in rupees
        age: Age (optional)
        state: State (optional, for state-specific schemes)
    
    Returns:
        Eligibility status and category
    """
    try:
        scheme = scheme.upper().strip()
        
        # PMAY-U income categories
        if "PMAY-U" in scheme or "PMAY" in scheme:
            if income <= 300000:
                return f"✅ ELIGIBLE for PMAY-U: EWS (Economically Weaker Section) Category (₹0-₹3L)"
            elif income <= 600000:
                return f"✅ ELIGIBLE for PMAY-U: LIG (Low Income Group) Category (₹3-₹6L)"
            elif income <= 900000:
                return f"✅ ELIGIBLE for PMAY-U: MIG (Middle Income Group) Category (₹6-₹9L)"
            else:
                return f"❌ NOT ELIGIBLE for PMAY-U: Income exceeds ₹9L limit"
        
        # PM-JAY (different eligibility)
        elif "PM-JAY" in scheme or "AYUSHMAN" in scheme:
            return "PM-JAY eligibility is based on SECC 2011 database, not income alone. Check state beneficiary lists."
        
        # PMJDY (no income limit)
        elif "PMJDY" in scheme or "JAN-DHAN" in scheme:
            return "✅ ELIGIBLE for PMJDY: No income criterion. Any unbanked adult can open a Jan-Dhan account."
        
        else:
            return f"Scheme '{scheme}' not recognized. Use search_schemes to find more info."
    
    except Exception as e:
        logger.error(f"Error in check_eligibility: {e}")
        return f"Error calculating eligibility: {str(e)}"


@tool
def fetch_user_profile(user_id: str) -> str:
    """
    Fetch user profile from Supabase (name, state, previously saved answers).
    
    Args:
        user_id: User WhatsApp number or session ID
    
    Returns:
        User profile data or message if not found
    """
    try:
        # Fetch from your existing session manager
        from app.db.session_manager import get_session
        session = get_session(user_id)
        
        if not session:
            return f"New user. No prior profile found for {user_id}"
        
        return f"User: {session.get('name', 'Unknown')}, State: {session.get('state', 'Not set')}, Income: ₹{session.get('income', '0')}"
    
    except Exception as e:
        logger.warning(f"Could not fetch user profile: {e}")
        return "Profile lookup unavailable"


# ============================================================================
# 4. WORKFLOW DEFINITION
# ============================================================================

def should_use_tools(state: AgentState) -> bool:
    """Determine if the agent should call tools or just respond."""
    last_message = state["messages"][-1]
    # If model sent ToolUse events, don't call tools again
    return not isinstance(last_message, ToolMessage)


def agent_node(state: AgentState) -> dict:
    """Main agent reasoning node"""
    # Build context from history
    conversation_messages = state["messages"]
    
    # System prompt
    system_prompt = """You are Sahayak AI, a professional WhatsApp assistant helping Indian citizens understand government schemes.

You have access to tools:
- search_schemes: Find scheme eligibility & details
- check_eligibility: Verify income-based eligibility  
- fetch_user_profile: Get user's prior context

Guidelines:
1. For scheme details → use search_schemes
2. For eligibility checks → use check_eligibility (ask for income if needed)
3. For personalized help → use fetch_user_profile
4. Keep responses under 500 characters for WhatsApp readability
5. Be warm, empowering, and clear
6. If info not in knowledge base, acknowledge limitations"""
    
    try:
        # Get next LLM instance from round-robin (load distribution + rate limit fallback)
        current_llm = get_next_gemini_llm()
        
        # Call LLM with tools
        response = current_llm.bind_tools(
            [search_schemes, check_eligibility, fetch_user_profile],
            tool_choice="auto"
        ).invoke(
            conversation_messages,
            system=system_prompt
        )
        
        # Add to message history
        state["messages"].append(response)
        return state
    
    except Exception as e:
        logger.error(f"Error in agent_node: {e}")
        error_msg = AIMessage(
            content=f"I encountered an error processing your request: {str(e)[:100]}. Please try again."
        )
        state["messages"].append(error_msg)
        return state


def tools_node(state: AgentState) -> dict:
    """Execute tools called by the agent"""
    message = state["messages"][-1]
    
    # Handle tool calls
    if hasattr(message, "tool_calls") and message.tool_calls:
        tool_map = {
            "search_schemes": search_schemes,
            "check_eligibility": check_eligibility,
            "fetch_user_profile": fetch_user_profile,
        }
        
        tool_results = []
        for tool_call in message.tool_calls:
            tool_name = tool_call["name"]
            tool_input = tool_call["args"]
            
            try:
                if tool_name in tool_map:
                    result = tool_map[tool_name].invoke(tool_input)
                    tool_results.append(
                        ToolMessage(
                            content=result,
                            tool_call_id=tool_call["id"],
                            name=tool_name
                        )
                    )
            except Exception as e:
                logger.error(f"Tool error {tool_name}: {e}")
                tool_results.append(
                    ToolMessage(
                        content=f"Error: {str(e)}",
                        tool_call_id=tool_call["id"],
                        name=tool_name
                    )
                )
        
        state["messages"].extend(tool_results)
    
    return state


def should_continue(state: AgentState) -> str:
    """Route to tools or end based on last message"""
    last_message = state["messages"][-1]
    
    # If last message has tool_calls, execute them
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    
    # Otherwise, end (response is ready)
    return "end"


# Build the graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tools_node)

# Add edges
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, {
    "tools": "tools",
    "end": END,
})
workflow.add_edge("tools", "agent")

# Compile with checkpointer
agent_app = workflow.compile(checkpointer=checkpointer)

logger.info("✅ LangGraph agent compiled successfully")


# ============================================================================
# 5. INVOCATION HELPER
# ============================================================================

def run_agent(
    user_message: str,
    thread_id: str,
    user_context: Dict[str, Any] = None
) -> str:
    """
    Run the agent and return the final response.
    
    Args:
        user_message: The WhatsApp message
        thread_id: User ID (for conversation memory)
        user_context: Optional dict with income, age, state
    
    Returns:
        Final bot response
    """
    try:
        # Initial state
        initial_state = AgentState(
            messages=[HumanMessage(content=user_message)],
            intent="general",
            user_context=user_context or {}
        )
        
        # Run with memory (checkpointer handles thread_id)
        config = {"configurable": {"thread_id": thread_id}}
        final_state = agent_app.invoke(initial_state, config=config)
        
        # Extract final response
        last_message = final_state["messages"][-1]
        response = last_message.content if hasattr(last_message, "content") else str(last_message)
        
        return response
    
    except Exception as e:
        logger.error(f"Agent error for {thread_id}: {e}")
        return "I'm sorry, I encountered an error. Please try again."
