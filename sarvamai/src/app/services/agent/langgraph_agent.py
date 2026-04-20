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

# Retry logic for rate limiting
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

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
from app.utils.text_preprocessing import preprocess_user_input

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
# Load all 4 Gemini keys into a list (Keys 4 & 6 removed - suspended/denied access)
API_KEYS = [
    settings.GEMINI_API_KEY1,
    settings.GEMINI_API_KEY2,
    settings.GEMINI_API_KEY3,
    settings.GEMINI_API_KEY5,
]

# Create an infinite cyclic iterator that rotates through all keys
gemini_key_cycle = itertools.cycle(API_KEYS)
logger.info(f"✅ Round-robin Gemini initialized with 4 API keys")

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


def call_gemini_with_retry(messages, tools, tool_choice="auto"):
    """
    Call Gemini with exponential backoff retry logic to handle 429 rate limit errors.
    If one key exhausts quota, try the next one automatically.
    
    ⚠️ IMPORTANT: Free tier limit is 20 requests/day per Google AI Studio project.
    All 4 API keys from the same account share this quota.
    If hitting rate limits:
    1. Upgrade to a paid plan: https://ai.google.dev/pricing
    2. OR wait for daily quota reset (UTC midnight)
    3. OR create separate Google Cloud projects for separate quotas
    
    Args:
        messages: List of messages to send to LLM
        tools: List of tools to bind
        tool_choice: Tool selection strategy
        
    Returns:
        LLM response with tools bound
    """
    @retry(
        stop=stop_after_attempt(4),  # Try up to 4 times (cycle through 4 keys)
        wait=wait_exponential(multiplier=2, min=5, max=60),  # 5s, 10s, 20s, 40s
        retry=retry_if_exception_type(Exception),  # Retry on any exception
        reraise=True  # Re-raise if all retries fail
    )
    def _call_gemini():
        llm = get_next_gemini_llm()
        return llm.bind_tools(tools, tool_choice=tool_choice).invoke(messages)
    
    try:
        return _call_gemini()
    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
            logger.warning(
                "⚠️ Rate limit (429) or quota exceeded on all Gemini API keys. "
                "Free tier: 20 requests/day per project (all keys share quota). "
                "Upgrade at: https://ai.google.dev/pricing"
            )
        raise



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
        
        # Search Qdrant using query_points (correct method for vector search)
        search_results = qdrant.query_points(
            collection_name="schemes",
            query=query_embedding,
            limit=4
        ).points
        
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
    Covers all 8 supported schemes: PMAY-U, PM-JAY, PMJDY, SSY, APY, PMUY, NSAP, Stand-Up India.
    
    Args:
        scheme: Scheme name (e.g., "PMAY-U", "PM-JAY", "SSY", "Sukanya Samriddhi")
        income: Annual income in rupees (optional, but helps with eligibility)
        age: Age (optional)
        state: State (optional, for state-specific schemes)
    
    Returns:
        Eligibility status with income categories and requirements
    """
    try:
        scheme = scheme.upper().strip()
        
        # PMAY-U income categories (Pradhan Mantri Awas Yojana - Urban)
        if "PMAY-U" in scheme or "PMAY" in scheme or "HOUSING" in scheme:
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
                result += "• EWS: ₹0-₹3L/year\n• LIG: ₹3-₹6L/year\n• MIG: ₹6-₹9L/year\n"
            result += "\nℹ️ Age: 18 years or older\nℹ️ BPL/APL both eligible if meet income criteria"
            return result
        
        # PM-JAY / Ayushman Bharat (health insurance)
        elif "PM-JAY" in scheme or "AYUSHMAN" in scheme or "BHARATI" in scheme:
            result = "🏥 **PM-JAY (Ayushman Bharat) - Health Insurance (₹5L coverage)**\n"
            if income:
                # SECC 2011 based income thresholds
                if income <= 300000:
                    result += f"✅ LIKELY ELIGIBLE: EWS category (₹0-₹3L)\n"
                elif income <= 600000:
                    result += f"✅ LIKELY ELIGIBLE: LIG category (₹3-₹6L)\n"
                else:
                    result += f"⚠️ May not be eligible based on income. Check SECC 2011 beneficiary list.\n"
            result += "\n📋 Eligibility based on: SECC 2011 data (rural deprivation + urban occupational)\n"
            result += "👉 Coverage: Hospitalization up to ₹5 lakhs per family per year"
            return result
        
        # PMJDY (Jan Dhan Yojana - Banking)
        elif "PMJDY" in scheme or "JAN-DHAN" in scheme or "BANK" in scheme:
            result = "💰 **PMJDY (Jan Dhan) - Universal Banking Account**\n"
            result += "✅ ELIGIBLE: Any Indian citizen 18+ without existing bank account\n"
            result += "ℹ️ No income limit\nℹ️ No age limit (children can also open)\n"
            result += "✨ Features: Zero balance, debit card, accident insurance, overdraft upto ₹10K"
            return result
        
        # SSY (Sukanya Samriddhi Yojana)
        elif "SSY" in scheme or "SUKANYA" in scheme or "GIRL" in scheme:
            result = "👧 **SSY (Sukanya Samriddhi Yojana) - Girl Child Savings**\n"
            if age and age >= 10:
                result += f"⚠️ INELIGIBLE: Account must be opened before age 10\n"
            elif age:
                result += f"✅ ELIGIBLE: Girl child is {age} years old (limit: before age 10)\n"
            else:
                result += "✅ ELIGIBLE: For any girl child below 10 years\n"
            result += "\nℹ️ No income criteria (any family can open)\n"
            result += "✨ Interest: 7.6%+ (government-backed)\n"
            result += "💰 Minimum deposit: ₹250/year; Maximum: ₹1.5L/year\n"
            result += "📅 Maturity: At age 21 or after 21 years (whichever is later)"
            return result
        
        # APY (Atal Pension Yojana)
        elif "APY" in scheme or "ATAL PENSION" in scheme or "PENSION" in scheme:
            result = "🎯 **APY (Atal Pension Yojana) - Guaranteed Pension**\n"
            if age and age >= 40:
                result += f"❌ INELIGIBLE: Age {age}. Entry age limit: 18-40 years\n"
            elif age:
                result += f"✅ ELIGIBLE: Age {age} (entry age 18-40)\n"
            else:
                result += "✅ ELIGIBLE: Ages 18-40 years\n"
            result += "\nℹ️ No income criteria\n"
            result += "💰 Pension: ₹1K-₹5K per month (guaranteed from age 60)\n"
            result += "✨ Government contribution: 50% of your contribution (for 5 years)"
            return result
        
        # PMUY (Pradhan Mantri Ujjwala Yojana)
        elif "PMUY" in scheme or "UJJWALA" in scheme or "GAS" in scheme or "CYLINDER" in scheme:
            result = "🔥 **PMUY (Ujjwala Yojana) - Free LPG Connection**\n"
            result += "✅ ELIGIBLE: BPL households + SC/ST households\n"
            result += "ℹ️ No income criteria (BPL status based)\n"
            result += "ℹ️ Female head of household preferred\n"
            result += "✨ Benefit: Free LPG connection + ₹1600 subsidy for stove"
            return result
        
        # NSAP (National Social Assistance Program)
        elif "NSAP" in scheme or "SOCIAL ASSISTANCE" in scheme or "PENSION" in scheme:
            result = "👴 **NSAP (National Social Assistance) - Old Age/Widow Pension**\n"
            result += "✅ Eligibility varies by state\n"
            if age and age >= 60:
                result += f"✅ Age {age}: Likely eligible for Old Age Pension\n"
            result += "ℹ️ Old Age Pension: Usually 60+ years (varies by state)\n"
            result += "ℹ️ Widow Pension: For widows below 60\n"
            result += "ℹ️ Disability Pension: For certified disabled persons\n"
            result += "💰 Amount: ₹200-₹500/month (varies by state)"
            return result
        
        # Stand-Up India
        elif "STAND-UP" in scheme or "STARTUP" in scheme or "ENTREPRENEURSHIP" in scheme:
            result = "🚀 **Stand-Up India - Entrepreneurship Loan**\n"
            result += "✅ ELIGIBLE: SC/ST/Women entrepreneurs\n"
            result += "ℹ️ Age: 18-40 years preferred\n"
            result += "💰 Loan: ₹10L - ₹1Cr at 7% interest\n"
            result += "✨ Collateral: Minimal/No collateral for loans up to ₹50L\n"
            result += "📋 Required: Business plan + bank tie-up"
            return result
        
        # Generic response for unknown schemes
        else:
            return f"📍 '{scheme}' - I don't have detailed eligibility in my database, but here's what matters for most schemes:\n\n✅ Income criteria: Usually EWS (₹0-3L), LIG (₹3-6L), MIG (₹6-9L)\n✅ Age: Typically 18+ years\n✅ Residency: Must be Indian citizen\n\n👉 Please ask about specific criteria or call web_search for current details."
    
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
            logger.warning("⚠️ SERPER_API_KEY not configured - web_search tool is disabled. Set it in Render dashboard for full functionality.")
            return "Web search temporarily unavailable (API key not configured). I can help with: PMAY-U 2.0, PMJDY, PMUY, Ayushman Bharat, NSAP, Sukanya Samriddhi, APY, Stand-Up India. Ask anything else and I'll try my best."
        
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
        
        # Validate and format results
        formatted_results = []
        for i, result in enumerate(results["organic"][:5], 1):
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            link = result.get("link", "")
            
            # Skip malformed results (missing title or snippet)
            if not title or not snippet:
                continue
            
            # Limit snippet to prevent too-long responses
            snippet = snippet[:150] if len(snippet) > 150 else snippet
            formatted_results.append(f"{i}. {title}\n   {snippet}\n   🔗 {link}")
        
        # Validate we have actual results
        if not formatted_results:
            logger.warning(f"⚠️ Web search returned no valid results for: {query[:50]}")
            return "No valid search results found. Try a different search term."
        
        result_text = "\n\n".join(formatted_results)
        logger.info(f"✅ Web search returned {len(formatted_results)} valid results for: {query[:50]}")
        return result_text
        
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
    eligibility_keywords = ["eligible", "category", "income", "fall under", "qualify", "bracket", "limit", "above", "below", "earn", "salary", "annual", "age", "requirements", "criteria", "who can", "can i", "am i", "eligibility", "requirement"]
    is_eligibility_question = any(kw in last_user_msg for kw in eligibility_keywords) if last_user_msg else False
    
    # Determine if this is a scheme/program question (should trigger search/web_search)
    scheme_keywords = ["scheme", "yojana", "program", "what is", "tell me", "information", "details", "how to", "apply", "benefits", "pm-", "pradhan mantri", "national", "ujjwala", "jan dhan", "sukanya", "atal", "awas", "ayushman", "samriddhi", "stand-up"]
    is_scheme_question = any(kw in last_user_msg for kw in scheme_keywords) if last_user_msg else False
    
    # 📖 Extract conversation summary for dynamic context
    conv_summary = _get_conversation_summary(conversation_messages)
    summary_section = f"\n\n📖 CONVERSATION CONTEXT:\n{conv_summary}" if conv_summary else ""
    
    # System prompt - NOW MUCH MORE AGGRESSIVE ABOUT TOOL USE
    system_prompt = f"""You are Sahayak AI, a professional WhatsApp assistant helping Indian citizens understand government schemes.

🚨 CRITICAL BEHAVIOR - FOLLOW 100%:
🚫 NEVER say "not in knowledge base" without calling tools FIRST
🚫 NEVER say "I don't have information" - use tools instead
🚫 NEVER respond with "I only support X schemes" - search for others instead
✅ For EVERY eligibility question → Call check_eligibility tool (even if you just answered about the scheme)
✅ For EVERY scheme name → Search it with search_schemes FIRST, then web_search if needed
✅ When unsure → Use web_search (don't guess or refuse)

USER ASKED ABOUT ELIGIBILITY? → CALL check_eligibility IMMEDIATELY
User says: "talk about eligibility" → You: [check_eligibility(last_scheme_mentioned)] → Answer
User says: "who is eligible" → You: [check_eligibility] → Answer
User says: "what's the age limit" → You: [check_eligibility(scheme, age=...)] → Answer

CONVERSATION RULES:
- You have FULL conversation history - use previous answers/context
- If you said "SSY is for girl child savings", and user says "eligibility?", you know the scheme - call check_eligibility("SSY")
- Never apologize for not having info - search for it instead
{summary_section}

THE 4 TOOLS - USE THEM AGGRESSIVELY:
1. search_schemes → For scheme details/application/process
2. web_search → For current/unknown/new schemes (PM NITI, latest changes)
3. check_eligibility → For income/age/criteria (ALWAYS for eligibility questions)
4. fetch_user_profile → For personalized answers (what schemes fit YOUR state/situation)

RESPONSE FORMAT:
- Be warm, clear, hopeful
- Give actionable steps
- Use emojis to highlight key info (✅, ❌, ℹ️, 💰, 🏠, etc)
- Keep under 500 chars for WhatsApp
- Always answer - never give up

EMPOWERMENT FIRST:
Users come to you for help improving their lives. Never crush that hope by saying:
- "I don't know"
- "Not in my knowledge base"  
- "I only support X schemes"
- "Information not available"
Instead: Use tools to find answers. ALWAYS."""
    
    try:
        # Determine if tools should be forced
        # Force for eligibility, scheme, or if conversation has existing context (follow-up)
        force_tools = is_eligibility_question or is_scheme_question or len(conversation_messages) > 1
        tool_choice = "any" if force_tools else "auto"
        
        # Prepend system prompt as SystemMessage (Gemini doesn't accept system= parameter)
        messages_with_system = [SystemMessage(content=system_prompt)] + conversation_messages
        
        # Log context for debugging
        logger.info(f"Tool forcing: force_tools={force_tools} (eligibility={is_eligibility_question}, scheme={is_scheme_question}, follow_up={len(conversation_messages) > 1})")
        
        # Call LLM with automatic retry on rate limits (exponential backoff with round-robin cycling)
        response = call_gemini_with_retry(
            messages_with_system,
            tools=[search_schemes, check_eligibility, fetch_user_profile, web_search],
            tool_choice=tool_choice  # Force or auto-select tools
        )
        
        # Log tool decision
        if hasattr(response, "tool_calls") and response.tool_calls:
            tool_names = [tc.get("name", "unknown") for tc in response.tool_calls]
            logger.info(f"🔧 Agent calling tools: {tool_names}")
        else:
            logger.info(f"Agent responding without tools (tool_choice={tool_choice}, force_tools={force_tools})")
        
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
            "web_search": web_search,
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
# 5. CONTEXT EXTRACTION HELPER
# ============================================================================

def _extract_recent_context(messages: List[BaseMessage], last_n_messages: int = 3) -> str:
    """
    Extract and format the last N messages from conversation history.
    Used to explicitly remind the agent of recent context.
    
    Args:
        messages: Full message history
        last_n_messages: Number of recent messages to extract (default 3)
        
    Returns:
        Formatted string with recent conversation context
    """
    if not messages:
        return ""
    
    # Get last N messages
    recent = messages[-last_n_messages:] if len(messages) > last_n_messages else messages
    
    context_lines = []
    for msg in recent:
        if isinstance(msg, HumanMessage):
            context_lines.append(f"👤 User: {msg.content[:100]}")
        elif isinstance(msg, AIMessage):
            context_lines.append(f"🤖 Assistant: {msg.content[:100]}")
        elif isinstance(msg, ToolMessage):
            context_lines.append(f"🔧 Tool({msg.name}): {msg.content[:100]}")
    
    return "\n".join(context_lines) if context_lines else ""


def _normalize_whatsapp_formatting(text: str) -> str:
    """
    Convert agent markdown to WhatsApp-compatible formatting.
    
    WhatsApp supports: *bold*, _italic_, ~strikethrough~, ```code```
    Convert: **bold** -> *bold*, __italic__ -> _italic_, # Headers -> *Header*
    """
    if not text:
        return text
    
    # Convert **bold** to *bold*
    text = text.replace("**", "*")
    
    # Convert __italic__ to _italic_
    text = text.replace("__", "_")
    
    # Convert # Headers to bold *Header*
    text = text.replace("# ", "*")
    text = text.replace("## ", "*")
    text = text.replace("### ", "*")
    
    # Clean up excess newlines (max 2 consecutive)
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    
    return text


def _get_conversation_summary(messages: List[BaseMessage]) -> str:
    """
    Create a brief summary of conversation topics mentioned.
    Used in system prompt to remind agent of discussion history.
    
    Args:
        messages: Full message history
        
    Returns:
        Summary of main schemes/topics discussed
    """
    if not messages or len(messages) < 2:
        return ""
    
    # Extract scheme names mentioned
    scheme_keywords = ['pmay', 'pm-jay', 'pmjdy', 'ssy', 'apy', 'pmuy', 'nsap', 'stand-up', 
                      'pm-kisan', 'nrega', 'ujjwala', 'ayushman', 'sukanya', 'atal', 'awas']
    
    topics_mentioned = set()
    for msg in messages:
        if isinstance(msg, (HumanMessage, AIMessage)):
            text = msg.content.lower()
            for scheme in scheme_keywords:
                if scheme in text:
                    topics_mentioned.add(scheme.upper())
    
    if topics_mentioned:
        return f"Topics discussed: {', '.join(sorted(topics_mentioned))}"
    
    return ""


# ============================================================================
# 6. INVOCATION HELPER
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
        # ✨ SPELL-CHECK & GRAMMAR CORRECTION
        # Preprocess user input to handle typos and grammatical errors
        corrected_message, original_message = preprocess_user_input(user_message)
        if corrected_message != original_message:
            logger.info(f"📝 Auto-corrected: '{original_message}' → '{corrected_message}'")
        
        # Load previous conversation history from checkpointer
        # This ensures the agent has full context of the conversation
        try:
            checkpoint = checkpointer.get(thread_id)
            previous_messages = checkpoint.get("values", {}).get("messages", []) if checkpoint else []
            if previous_messages:
                logger.info(f"✅ Loaded {len(previous_messages)} previous messages from checkpoint for {thread_id}")
            else:
                logger.info(f"ℹ️ No previous checkpoint for {thread_id} - starting fresh conversation")
        except Exception as e:
            logger.warning(f"⚠️ Could not load checkpoint for {thread_id}: {e}. Starting fresh.")
            previous_messages = []
        
        # ============================================================================
        # 💾 CONTEXT GATHERING - Extract last 2-3 messages for explicit awareness
        # ============================================================================
        recent_context = _extract_recent_context(previous_messages, last_n_messages=3)
        
        if recent_context:
            logger.info(f"📖 Recent conversation (last 2-3 turns):\n{recent_context}")
        
        # Build messages: previous history + corrected user message
        all_messages = list(previous_messages) if previous_messages else []
        all_messages.append(HumanMessage(content=corrected_message))
        
        logger.info(f"💬 Total conversation: {len(all_messages)} messages | Recent context extracted for agent awareness")
        
        # Initial state with full conversation history
        initial_state = AgentState(
            messages=all_messages,
            intent="general",
            user_context=user_context or {}
        )
        
        # Run with memory (checkpointer handles thread_id)
        config = {"configurable": {"thread_id": thread_id}}
        final_state = agent_app.invoke(initial_state, config=config)
        
        # Extract final response (handle both string and structured content)
        last_message = final_state["messages"][-1]
        
        # Get raw content
        raw_content = last_message.content if hasattr(last_message, "content") else str(last_message)
        
        # Handle structured content (list of dicts from some LLMs)
        if isinstance(raw_content, list):
            # Extract text from list of content blocks
            text_parts = []
            for block in raw_content:
                if isinstance(block, dict) and "text" in block:
                    text_parts.append(block["text"])
                elif isinstance(block, str):
                    text_parts.append(block)
            response = "\n".join(text_parts) if text_parts else str(raw_content)
        # Handle dict content (single structured response)
        elif isinstance(raw_content, dict) and "text" in raw_content:
            response = raw_content["text"]
        # Handle plain string (most common)
        elif isinstance(raw_content, str):
            response = raw_content
        # Fallback
        else:
            response = str(raw_content)
        
        # 🎨 WHATSAPP TEXT FORMATTING - Normalize markdown for WhatsApp compatibility
        response = _normalize_whatsapp_formatting(response)
        
        logger.info(f"✅ Agent response for {thread_id}: {response[:100]}...")
        return response
    
    except Exception as e:
        logger.error(f"Agent error for {thread_id}: {e}")
        return "I'm sorry, I encountered an error. Please try again."
