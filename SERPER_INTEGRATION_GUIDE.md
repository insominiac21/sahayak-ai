# Google Serper Integration for Agentic Web Search
## Quick Implementation Guide

---

## 1. SETUP (5 minutes)

### Step 1: Get API Key
```
1. Go to https://serper.dev
2. Sign up (free tier = 100 searches/month)
3. Get API key from dashboard
4. Add to .env:
   SERPER_API_KEY=your_key_here
```

### Step 2: Install Dependencies
```bash
pip install httpx  # Already in your dependencies
```

---

## 2. COMPLETE IMPLEMENTATION

### File: `sarvamai/src/app/services/chat/web_search_tool.py`

```python
"""
Web search tool using Google Serper API
Enables agent to search for current, time-sensitive information
Examples: "PM-Kisan next installment date", "APY interest rate 2024"
"""

import os
import httpx
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class SerperWebSearch:
    """Google Serper API wrapper for agentic web search"""
    
    def __init__(self):
        self.api_key = os.getenv("SERPER_API_KEY")
        self.base_url = "https://google.serper.dev/search"
        self.timeout = 3.0  # 3-second timeout for agent loop
        
        if not self.api_key:
            logger.warning("SERPER_API_KEY not set. Web search disabled.")
    
    def search(
        self,
        query: str,
        num_results: int = 5,
        include_snippets: bool = True,
    ) -> Dict:
        """
        Search Google using Serper API
        
        Args:
            query: Search query (e.g., "PM-Kisan installment 2024")
            num_results: Number of results to return (default 5)
            include_snippets: Include result summaries
        
        Returns:
            {
                "success": bool,
                "query": str,
                "results": [
                    {
                        "title": str,
                        "url": str,
                        "snippet": str
                    }
                ]
            }
        """
        
        if not self.api_key:
            return {
                "success": False,
                "error": "SERPER_API_KEY not configured",
            }
        
        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "q": query,
            "num": num_results,
        }
        
        try:
            response = httpx.post(
                self.base_url,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Format results
                results = []
                for organic_result in data.get("organic", []):
                    results.append({
                        "title": organic_result.get("title", ""),
                        "url": organic_result.get("link", ""),
                        "snippet": organic_result.get("snippet", "") if include_snippets else "",
                    })
                
                return {
                    "success": True,
                    "query": query,
                    "results": results,
                }
            
            else:
                logger.error(f"Serper API error: {response.status_code}")
                return {
                    "success": False,
                    "error": f"API error: {response.status_code}",
                }
        
        except httpx.TimeoutException:
            logger.warning(f"Web search timeout for query: {query}")
            return {
                "success": False,
                "error": "Search timed out (>3s)",
            }
        
        except Exception as e:
            logger.exception(f"Web search failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    def format_for_agent(self, search_result: Dict) -> str:
        """Format search results as observation for agent"""
        
        if not search_result.get("success"):
            return f"Web search failed: {search_result.get('error')}"
        
        formatted = f"Web search results for '{search_result['query']}':\n\n"
        
        for i, result in enumerate(search_result['results'], 1):
            formatted += f"[{i}] {result['title']}\n"
            if result['snippet']:
                formatted += f"    {result['snippet']}\n"
            formatted += f"    Source: {result['url']}\n\n"
        
        return formatted


# Singleton instance
_web_search = None

def get_web_search() -> SerperWebSearch:
    """Get singleton web search instance"""
    global _web_search
    if _web_search is None:
        _web_search = SerperWebSearch()
    return _web_search
```

---

## 3. INTEGRATE INTO AGENTIC ORCHESTRATOR

### File: `sarvamai/src/app/services/chat/agentic_orchestrator.py`

```python
"""
Agentic Orchestrator with Tool Calling Loop
Integrates Phase 1 (Retrieval) + Phase 2 (Memory) + Phase 3 (Agency)
"""

import logging
import json
from typing import Optional, List, Dict
from datetime import datetime

from app.services.chat.session_manager import SessionManager
from app.services.chat.intent_classifier import IntentClassifier
from app.services.chat.query_reformulator import QueryReformulator
from app.services.chat.context_injector import ContextInjector
from app.services.rag.two_stage_retriever import TwoStageRetriever
from app.services.chat.eligibility_calculator import EligibilityCalculator  # Phase 3 tool
from app.services.chat.web_search_tool import get_web_search  # Phase 3 tool
from app.core.config import SETTINGS

logger = logging.getLogger(__name__)


class AgenticOrchestrator:
    """
    Orchestrates agentic loop with tool calling.
    
    Architecture:
    1. Session Management (Phase 2)
    2. Intent Detection (Phase 2)
    3. Query Reformulation (Phase 2)
    4. AGENTIC LOOP (Phase 3):
        - LLM reasons: "What tools do I need?"
        - Calls tools: eligibility_calc, vector_search, web_search
        - Observes results
        - Chains next tool based on observation
        - Repeats until max_steps or "FINAL_ANSWER"
    5. Response synthesis
    6. Database storage
    """
    
    MAX_STEPS = 5  # Prevent infinite loops
    LLM_TIMEOUT = 15.0  # Seconds
    
    def __init__(self):
        self.session_manager = SessionManager()
        self.intent_classifier = IntentClassifier()
        self.query_reformulator = QueryReformulator()
        self.context_injector = ContextInjector()
        self.retriever = TwoStageRetriever()
        self.eligibility_calc = EligibilityCalculator()
        self.web_search = get_web_search()
    
    def process_message(
        self,
        phone_number: str,
        user_message: str,
        language: str = "en",
    ) -> Dict:
        """
        Process user message through full agentic pipeline
        
        Args:
            phone_number: User's WhatsApp number (e.g., "+919876543210")
            user_message: User's message text
            language: Detected language (en, hi, ta, te)
        
        Returns:
            {
                "session_id": str,
                "response": str,
                "steps_taken": int,
                "tools_used": List[str],
                "latency_ms": int,
            }
        """
        
        start_time = datetime.utcnow()
        tools_used = []
        
        try:
            # ========== PHASE 2 ==========
            
            # Step 1: Session Management
            session = self.session_manager.get_or_create_session(
                phone_number=phone_number,
                language=language,
            )
            
            # Step 2: Intent Classification
            intent, confidence = self.intent_classifier.classify(user_message)
            scheme = self.intent_classifier.extract_scheme(user_message)
            
            # Step 3: Query Reformulation (for follow-ups)
            should_reform = self.query_reformulator.is_reformulation_needed(
                query=user_message,
                context=self.session_manager.get_context_for_follow_up(session.session_id),
            )
            if should_reform:
                user_message = self.query_reformulator.reformulate(user_message, scheme)
            
            # Step 4: Context Injection
            context_window = self.context_injector.build_context_window(
                scheme_name=scheme,
                intent=intent,
                session_id=session.session_id,
                session_manager=self.session_manager,
            )
            
            # ========== PHASE 3: AGENTIC LOOP ==========
            
            response, tools_used = self._agentic_loop(
                user_message=user_message,
                context_window=context_window,
                session=session,
            )
            
            # ========== STORAGE ==========
            
            # Add turn to session history
            self.session_manager.add_turn(
                session_id=session.session_id,
                user_message=user_message,
                bot_response=response,
                user_message_reformulated=user_message if should_reform else None,
                intent_detected=intent,
                retrieved_scheme_names=[scheme] if scheme else [],
            )
            
            # ========== RETURN ==========
            
            latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return {
                "session_id": session.session_id,
                "response": response,
                "steps_taken": len(tools_used),
                "tools_used": tools_used,
                "latency_ms": latency_ms,
                "success": True,
            }
        
        except Exception as e:
            logger.exception(f"Orchestrator failed for {phone_number}: {e}")
            return {
                "response": "Sorry, something went wrong. Please try again.",
                "success": False,
                "error": str(e),
            }
    
    def _agentic_loop(
        self,
        user_message: str,
        context_window: Dict,
        session,
    ) -> tuple[str, List[str]]:
        """
        Run the agentic loop with tool calling
        
        Returns:
            (final_response: str, tools_used: List[str])
        """
        
        observations = []
        tools_used = []
        step = 0
        
        system_prompt = """You are Sahayak AI, a government scheme assistant.
You have access to these tools:
- eligibility_calc(income, family_size, scheme_name): Check if user qualifies
- vector_search(query): Search scheme documentation
- web_search(query): Search current news and updates

Instructions:
1. THINK about what information you need to answer the user
2. Use tools to gather information
3. When you have enough info, provide FINAL_ANSWER

Always respond in this format:
THOUGHT: <what you're thinking>
ACTION: <tool_name>(arg1, arg2)

When ready to answer:
FINAL_ANSWER: <your response>
"""
        
        while step < self.MAX_STEPS:
            
            # Build conversation for LLM
            messages = [
                {
                    "role": "user",
                    "content": user_message,
                }
            ]
            
            if observations:
                messages.append({
                    "role": "assistant",
                    "content": "\n".join(observations),
                })
            
            # Get LLM response
            try:
                llm_response = self._call_gemini(system_prompt, messages)
            except Exception as e:
                logger.warning(f"LLM call failed: {e}")
                return "I couldn't process that. Please try again.", tools_used
            
            logger.debug(f"LLM Response (Step {step}): {llm_response}")
            
            # Parse LLM response
            if "FINAL_ANSWER:" in llm_response:
                final_answer = llm_response.split("FINAL_ANSWER:")[-1].strip()
                return final_answer, tools_used
            
            if "ACTION:" in llm_response:
                # Extract tool call
                try:
                    action_str = llm_response.split("ACTION:")[-1].strip()
                    tool_call = self._parse_tool_call(action_str)
                    
                    if tool_call:
                        tool_name, tool_args = tool_call
                        
                        # Execute tool
                        observation = self._execute_tool(tool_name, tool_args)
                        observations.append(f"OBSERVATION: {observation}")
                        tools_used.append(tool_name)
                        step += 1
                    else:
                        break
                
                except Exception as e:
                    logger.warning(f"Tool execution failed: {e}")
                    observations.append(f"OBSERVATION: Tool failed - {str(e)}")
                    step += 1
            
            else:
                # LLM didn't respond with tool call or final answer
                logger.warning(f"Unexpected LLM format: {llm_response}")
                break
        
        # Fallback: force final answer after max steps
        return f"Based on my search, I found: {observations[-1] if observations else 'Unable to find info.'}", tools_used
    
    def _call_gemini(self, system_prompt: str, messages: List[Dict]) -> str:
        """Call Gemini API with timeout"""
        import google.generativeai as genai
        
        client = genai.Client(api_key=SETTINGS.gemini_api_key)
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                {"role": "user", "parts": [{"text": system_prompt}]},
                *messages,
            ],
            timeout=self.LLM_TIMEOUT,
        )
        
        return response.text
    
    def _execute_tool(self, tool_name: str, tool_args: Dict) -> str:
        """Execute a tool and return observation"""
        
        try:
            if tool_name == "eligibility_calc":
                result = self.eligibility_calc.calculate(**tool_args)
                return f"Eligibility check result: {result}"
            
            elif tool_name == "vector_search":
                chunks = self.retriever.retrieve(query=tool_args.get("query", ""))
                return f"Found {len(chunks)} relevant docs: {chunks[0]['text'][:200]}..."
            
            elif tool_name == "web_search":
                search_result = self.web_search.search(query=tool_args.get("query", ""))
                return self.web_search.format_for_agent(search_result)
            
            else:
                return f"Unknown tool: {tool_name}"
        
        except Exception as e:
            logger.exception(f"Tool {tool_name} failed: {e}")
            return f"Tool {tool_name} failed: {str(e)}"
    
    def _parse_tool_call(self, action_str: str) -> Optional[tuple[str, Dict]]:
        """Parse 'tool_name(arg1=val1, arg2=val2)' format"""
        try:
            # Extract tool name and args
            if "(" not in action_str or ")" not in action_str:
                return None
            
            tool_name = action_str.split("(")[0].strip()
            args_str = action_str.split("(")[1].split(")")[0]
            
            # For simplicity, assume args are comma-separated key=value
            args = {}
            for pair in args_str.split(","):
                if "=" in pair:
                    key, val = pair.split("=")
                    args[key.strip()] = val.strip().strip('"').strip("'")
            
            return (tool_name, args)
        
        except Exception as e:
            logger.warning(f"Failed to parse tool call: {e}")
            return None
```

---

## 4. ELIGIBILITY CALCULATOR TOOL

### File: `sarvamai/src/app/services/chat/eligibility_calculator.py`

```python
"""
Eligibility Calculator Tool for Agentic AI
Performs mathematical calculations for scheme eligibility
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class EligibilityCalculator:
    """
    Calculate scheme eligibility based on hardcoded rules.
    
    Examples:
    - PM-KISAN: Annual income < 2 Crore
    - PMAY-U: Family income < 6 Lakh (EWS), 6-18 Lakh (LIG), 18-30 Lakh (MIG)
    - APY: Age 18-60 for contribution
    """
    
    SCHEME_RULES = {
        "pm-kisan": {
            "income_limit": 200_000_000,  # 2 Crore
            "categories": {
                "eligible": (0, 200_000_000),
            }
        },
        "pmay-u": {
            "ews": (0, 300_000),
            "lig": (300_000, 600_000),
            "mig_i": (600_000, 1_200_000),
            "mig_ii": (1_200_000, 1_800_000),
        },
        "apy": {
            "min_age": 18,
            "max_age": 60,
        },
        "nsap": {
            "age_min_elderly": 60,
            "age_min_widow": 18,
            "income_limit": 50_000,
        },
    }
    
    def calculate(self, income: int, scheme_name: str, **kwargs) -> str:
        """
        Check eligibility for scheme
        
        Args:
            income: Annual income in INR
            scheme_name: Scheme identifier (e.g., "pm-kisan")
            **kwargs: Additional params (age, family_size, etc.)
        
        Returns:
            Eligibility statement (e.g., "Eligible: EWS category")
        """
        
        scheme = scheme_name.lower().strip()
        
        if scheme not in self.SCHEME_RULES:
            return f"Unknown scheme: {scheme}"
        
        if scheme == "pm-kisan":
            return self._check_pm_kisan(income)
        elif scheme == "pmay-u":
            return self._check_pmay_u(income, kwargs.get("family_size", 1))
        elif scheme == "apy":
            return self._check_apy(kwargs.get("age", 0))
        elif scheme == "nsap":
            return self._check_nsap(kwargs.get("age", 0), income)
        else:
            return "Eligibility calculation not available for this scheme"
    
    def _check_pm_kisan(self, income: int) -> str:
        limit = self.SCHEME_RULES["pm-kisan"]["income_limit"]
        if income <= limit:
            return f"✓ Eligible for PM-KISAN (Annual income: {income:,})"
        else:
            return f"✗ Not eligible (Annual income exceeds ₹2 Crore limit)"
    
    def _check_pmay_u(self, income: int, family_size: int) -> str:
        """Check housing scheme eligibility"""
        rules = self.SCHEME_RULES["pmay-u"]
        
        if income <= rules["ews"][1]:
            return f"✓ Eligible: EWS category (Annual income: {income:,})"
        elif income <= rules["lig"][1]:
            return f"✓ Eligible: LIG category (Annual income: {income:,})"
        elif income <= rules["mig_i"][1]:
            return f"✓ Eligible: MIG-I category (Annual income: {income:,})"
        elif income <= rules["mig_ii"][1]:
            return f"✓ Eligible: MIG-II category (Annual income: {income:,})"
        else:
            return f"✗ Not eligible (Annual income exceeds ₹18 Lakh limit)"
    
    def _check_apy(self, age: int) -> str:
        """Check pension scheme eligibility"""
        min_age = self.SCHEME_RULES["apy"]["min_age"]
        max_age = self.SCHEME_RULES["apy"]["max_age"]
        
        if min_age <= age <= max_age:
            return f"✓ Eligible for APY (Age: {age})"
        else:
            return f"✗ Not eligible (APY requires age 18-60, you are {age})"
    
    def _check_nsap(self, age: int, income: int) -> str:
        """Check pension scheme eligibility"""
        rules = self.SCHEME_RULES["nsap"]
        
        if age >= rules["age_min_elderly"]:
            if income <= rules["income_limit"]:
                return f"✓ Eligible for NSAP (Elderly pension)"
            else:
                return f"✗ Income exceeds limit (₹50,000/year)"
        else:
            return f"✗ Not eligible (Requires age 60+, you are {age})"
```

---

## 5. ADD TO ENVIRONMENT

### `.env` file
```
SERPER_API_KEY=your_serper_api_key_here
```

### `pyproject.toml`
```toml
dependencies = [
    # ... existing ...
    "httpx>=0.28.1",  # Already there for Serper
]
```

---

## 6. USAGE EXAMPLE

### How Agent Uses Serper

```
User: "I earn ₹2.5L per year. Which housing scheme can I apply for?"

Agent Flow:
  THOUGHT: User is asking about housing. Need income + scheme eligibility.
  ACTION: eligibility_calc(income=250000, scheme_name="pmay-u")
  OBSERVATION: "✓ Eligible: EWS category"
  
  THOUGHT: Good, but policy might have changed. Let me check current info.
  ACTION: web_search(query="PMAY-U latest updates 2024")
  OBSERVATION: "PMAY-U new rules: ... increased subsidy... application deadline..."
  
  THOUGHT: Now get document details.
  ACTION: vector_search(query="PMAY-U EWS documents required")
  OBSERVATION: "Found docs: 1) Aadhar 2) Income certificate 3) Property docs"
  
  FINAL_ANSWER: "You qualify for PMAY-U in EWS category! 
                 Recent updates show increased subsidy (2024).
                 Documents needed: [detailed list]
                 Next step: Apply through official portal by [date]"
```

---

## 7. TESTING SERPER LOCALLY

```python
# Quick test
from app.services.chat.web_search_tool import SerperWebSearch

web_search = SerperWebSearch()
result = web_search.search("PM-Kisan installment 2024")
print(web_search.format_for_agent(result))
```

---

## 8. COST TRACKING

Serper pricing:
- Free tier: 100 searches/month
- Paid: $5/500 searches

Track usage:
```python
# In agentic_orchestrator.py
if tool_name == "web_search":
    log_serper_usage(query, cost_per_query=0.01)
```

---

**Summary:** Google Serper makes your agent aware of real-world, time-sensitive information. Combined with eligibility calculator and vector search, this is a truly powerful agentic system.
