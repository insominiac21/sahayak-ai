"""
Phase 3: LangGraph Agent for Sahayak AI
Handles multi-step reasoning with tools: scheme search, eligibility calc, web search
Uses Supabase Postgres checkpointer for persistent memory.
"""

import os
import logging
import itertools
import requests
from typing import Annotated, Any, Dict, List, TypedDict
from dotenv import load_dotenv

# Core LangGraph imports
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

# LangChain imports
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage, SystemMessage
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
        
        # Validate embedding (check length instead of truthiness to avoid numpy ambiguity)
        if len(query_embedding) == 0:
            return "Error: Failed to generate query embedding"
        
        # Search Qdrant
        search_results = qdrant.search(
            collection_name="schemes",
            query_vector=query_embedding,
            limit=4
        )
        
        if not search_results:
            # Don't be defensive - tell agent to use web_search
            return f"Scheme not found in my current knowledge base. Please call web_search('{query}') to find current information."
        
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
def check_eligibility(scheme: str, income: int = None, age: int = None, state: str = None) -> str:
    """
    Check eligibility for a specific scheme based on income and demographics.
    Use this tool when user asks about income categories or eligibility.
    
    Args:
        scheme: Scheme name (e.g., "PMAY-U", "PM-JAY", "PMJDY", "Ayushman Bharat")
        income: Annual income in rupees (optional, but helps with eligibility)
        age: Age (optional)
        state: State (optional, for state-specific schemes)
    
    Returns:
        Eligibility status with income categories and requirements
    """
    try:
        scheme = scheme.upper().strip()
        
        # PMAY-U income categories (Pradhan Mantri Awas Yojana - Urban)
        if "PMAY-U" in scheme or "PMAY" in scheme:
            result = "🏠 **PMAY-U (Urban Housing) Income Categories:**\n"
            if income:
                if income <= 300000:
                    result += f"✅ YOUR CATEGORY: EWS (₹0-₹3L/year)\n"
                elif income <= 600000:
                    result += f"✅ YOUR CATEGORY: LIG (₹3-₹6L/year)\n"
                elif income <= 900000:
                    result += f"✅ YOUR CATEGORY: MIG (₹6-₹9L/year)\n"
                else:
                    result += f"❌ NOT ELIGIBLE: Income exceeds ₹9L/year limit\n"
            else:
                result += "• EWS: ₹0-₹3L/year\n• LIG: ₹3-₹6L/year\n• MIG: ₹6-₹9L/year"
            return result
        
        # PM-JAY / Ayushman Bharat (health insurance)
        elif "PM-JAY" in scheme or "AYUSHMAN" in scheme or "BHARATI" in scheme:
            result = "🏥 **PM-JAY (Ayushman Bharat) - Health Insurance**\n"
            if income:
                # SECC 2011 based income thresholds
                if income <= 300000:
                    result += f"✅ LIKELY ELIGIBLE: EWS category (based on SECC 2011)\n"
                elif income <= 600000:
                    result += f"✅ LIKELY ELIGIBLE: LIG category (based on SECC 2011)\n"
                else:
                    result += f"⚠️ May not be eligible based on income. Check SECC 2011 database for your state.\n"
            result += "\n📋 Full eligibility based on: Socio-Economic Caste Census (SECC 2011) + state additions\n"
            result += "👉 Check your state's beneficiary list on PM-JAY website"
            return result
        
        # PMJDY (Jan Dhan Yojana - Banking)
        elif "PMJDY" in scheme or "JAN-DHAN" in scheme:
            return "💰 **PMJDY (Jan Dhan) - Universal Banking**\n✅ ELIGIBLE: Anyone 18+ without existing bank account\n❌ No income limit or restriction"
        
        # Generic response for unknown schemes
        else:
            # Don't be defensive - encourage web_search instead
            return f"📍 '{scheme}' eligibility details not in my database.\n👉 Calling web_search to find current information about '{scheme}' for you...\n\nEligibility usually depends on: income, age, state, occupation, and social category. Let me find the official requirements."
    
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


@tool
def web_search(query: str) -> str:
    """
    Search Google using Serper API for current/real-time information.
    Use this when knowledge base doesn't have the answer.
    
    Args:
        query: Search query (e.g., "PMAY-U eligibility 2024", "latest housing schemes")
    
    Returns:
        Top search results with snippets and links
    """
    try:
        if not settings.SERPER_API_KEY:
            return "Web search unavailable: SERPER_API_KEY not configured"
        
        # Call Serper API
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": settings.SERPER_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {"q": query, "num": 5}  # Get top 5 results
        
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        response.raise_for_status()
        
        results = response.json()
        
        # Format results
        if "organic" not in results or not results["organic"]:
            return "No search results found for your query."
        
        formatted_results = []
        for i, result in enumerate(results["organic"][:5], 1):
            title = result.get("title", "No title")
            snippet = result.get("snippet", "No snippet")[:150]  # Limit snippet length
            link = result.get("link", "")
            formatted_results.append(f"{i}. {title}\n   {snippet}\n   Link: {link}")
        
        return "\n\n".join(formatted_results)
        
    except requests.exceptions.Timeout:
        logger.error("Serper API request timeout")
        return "Search timed out. Please try again."
    except requests.exceptions.RequestException as e:
        logger.error(f"Serper API error: {e}")
        return f"Search error: {str(e)[:100]}"
    except Exception as e:
        logger.error(f"Error in web_search tool: {e}")
        return "Web search temporarily unavailable"


# ============================================================================
# 4. WORKFLOW DEFINITION
# ============================================================================

def should_use_tools(state: AgentState) -> bool:
    """Determine if the agent should call tools or just respond."""
    last_message = state["messages"][-1]
    # If model sent ToolUse events, don't call tools again
    return not isinstance(last_message, ToolMessage)


def agent_node(state: AgentState) -> dict:
    """Main agent reasoning node with intelligent tool selection"""
    # Build context from history
    conversation_messages = state["messages"]
    
    # Analyze conversation to understand what's being asked
    last_user_msg = None
    for msg in reversed(conversation_messages):
        if isinstance(msg, HumanMessage):
            last_user_msg = msg.content.lower()
            break
    
    # Determine if this is an eligibility/income question
    eligibility_keywords = ["eligible", "category", "income", "fall under", "qualify", "bracket", "limit", "above", "below", "earn", "salary", "annual"]
    is_eligibility_question = any(kw in last_user_msg for kw in eligibility_keywords) if last_user_msg else False
    
    # Determine if this is a scheme/program question (should trigger search/web_search)
    scheme_keywords = ["scheme", "yojana", "program", "what is", "tell me about", "information about", "details about", "how to", "apply for", "benefits of", "pm-", "pradhan mantri", "national"]
    is_scheme_question = any(kw in last_user_msg for kw in scheme_keywords) if last_user_msg else False
    
    # System prompt - NOW MUCH MORE AGGRESSIVE ABOUT TOOL USE
    system_prompt = """You are Sahayak AI, a professional WhatsApp assistant helping Indian citizens understand government schemes.

CRITICAL RULES - FOLLOW STRICTLY:
🚫 NEVER EVER say "I don't have information" or "not in knowledge base" or "I don't support that scheme"
   INSTEAD: Always call tools first - search_schemes OR web_search - BEFORE responding
🚫 NEVER give up on user questions - you have tools to find answers
✅ For ANY scheme question → try search_schemes FIRST, then web_search if KB doesn't have it
✅ For eligibility questions → ALWAYS call check_eligibility with user's income/context
✅ For unknown schemes → use web_search (don't just say you don't know)

CONVERSATION CONTEXT:
- Review ENTIRE conversation history before responding
- Use info from earlier responses - if you said "LIG is ₹3L-₹6L" and user says "I earn 5L", match to LIG
- Apply reasoning: don't repeat the same info, build on previous answers

TOOLS - USE THEM:
- search_schemes(query): Search knowledge base for scheme details (PMAY-U, PM-JAY, PMJDY, etc.)
- check_eligibility(scheme, income): Verify if user qualifies (EWS/LIG/MIG categories)
- fetch_user_profile(user_id): Get user's saved info (state, income, name)
- web_search(query): Search Google for current/new schemes or info not in KB (PM NITI AYOG, latest schemes, etc.)

DECISION FLOW:
1. Is this about a specific scheme? → call search_schemes(scheme_name)
2. Did KB search return nothing? → call web_search(scheme_name) to find current info
3. Is user asking about eligibility/income? → call check_eligibility with their numbers
4. User asks "search for it"? → DO web_search IMMEDIATELY
5. Your last response was "I don't have data"? → You made a MISTAKE - should have called web_search

RESPONSE GUIDELINES:
- Always be helpful and hopeful - schemes exist to help Indians
- If you don't immediately know something, search for it (don't apologize, just do it)
- Keep responses under 500 chars for WhatsApp
- Use emojis and formatting to make info clear (🏠, 💰, ✅, ❌)

EXAMPLES:
- User: "Tell me about PM NITI AYOG" → You: [search_schemes('PM NITI AYOG')] → [web_search('PM NITI AYOG 2024')] → Give full answer
- User: "My income is 5 lakhs" → You: [check_eligibility('PMAY-U', 500000)] → Explain which categories they fit
- User: "I don't know any schemes" → You: [search_schemes('government schemes for housing')] → List 3-4 with benefits

EMPOWERMENT:
- Users come to you hoping to improve their lives
- Don't crush that hope by saying "I don't have information"
- Use tools to deliver answers, every single time"""
    
    try:
        # Get next LLM instance from round-robin (load distribution + rate limit fallback)
        current_llm = get_next_gemini_llm()
        
        # Force tool use for eligibility OR scheme questions
        tool_choice = "any" if (is_eligibility_question or is_scheme_question) else "auto"
        
        
        # Prepend system prompt as SystemMessage (Gemini doesn't accept system= parameter)
        messages_with_system = [SystemMessage(content=system_prompt)] + conversation_messages
        
        # Call LLM with tools
        response = current_llm.bind_tools(
            [search_schemes, check_eligibility, fetch_user_profile, web_search],
            tool_choice=tool_choice  # Force or auto-select tools
        ).invoke(messages_with_system)
        
        # Log tool decision
        if hasattr(response, "tool_calls") and response.tool_calls:
            tool_names = [tc.get("function", {}).get("name", "unknown") for tc in response.tool_calls]
            logger.info(f"🔧 Agent calling tools: {tool_names}")
        else:
            logger.debug("Agent responding without tools")
        
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
        # Load previous conversation history from checkpointer
        # This ensures the agent has full context of the conversation
        try:
            checkpoint = checkpointer.get(thread_id)
            previous_messages = checkpoint.get("values", {}).get("messages", []) if checkpoint else []
        except Exception as e:
            logger.debug(f"Could not load checkpoint for {thread_id}: {e}. Starting fresh.")
            previous_messages = []
        
        # Build messages: previous history + new user message
        all_messages = list(previous_messages) if previous_messages else []
        all_messages.append(HumanMessage(content=user_message))
        
        logger.debug(f"Agent running with {len(all_messages)} messages in conversation history")
        
        # Initial state with full conversation history
        initial_state = AgentState(
            messages=all_messages,
            intent="general",
            user_context=user_context or {}
        )
        
        # Run with memory (checkpointer handles thread_id)
        config = {"configurable": {"thread_id": thread_id}}
        final_state = agent_app.invoke(initial_state, config=config)
        
        # Extract final response
        last_message = final_state["messages"][-1]
        response = last_message.content if hasattr(last_message, "content") else str(last_message)
        
        logger.info(f"✅ Agent response for {thread_id}: {response[:100]}...")
        return response
    
    except Exception as e:
        logger.error(f"Agent error for {thread_id}: {e}")
        return "I'm sorry, I encountered an error. Please try again."
