#!/usr/bin/env python3
"""
Local testing script for LangGraph agent WITHOUT Twilio webhooks.
Tests context window, tool calling, and logs directly.
"""

import os
import sys
import logging
import io

# Fix Windows encoding issues
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='ignore')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='ignore')

# Setup logging to see everything
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

# Add sarvamai/src to path so we can import app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sarvamai/src'))

from app.services.agent.langgraph_agent import run_agent

def test_context_window():
    """Test if context window is preserved across messages"""
    thread_id = "test_user_123"
    
    print("\n" + "="*80)
    print("TEST 1: Context Window (Multi-turn conversation)")
    print("="*80)
    
    # Message 1: Ask about a scheme
    print("\nMessage 1: 'Tell me about PMUY'")
    response1 = run_agent(
        user_message="Tell me about PMUY",
        thread_id=thread_id,
        user_context={}
    )
    print(f"Response 1:\n{response1}\n")
    
    # Message 2: Follow-up about eligibility
    print("Message 2: 'Who is eligible?'")
    response2 = run_agent(
        user_message="Who is eligible?",
        thread_id=thread_id,
        user_context={}
    )
    print(f"Response 2:\n{response2}\n")
    
    # Message 3: Another follow-up
    print("Message 3: 'Can I take it on my mother's name?'")
    response3 = run_agent(
        user_message="Can I take it on my mother's name?",
        thread_id=thread_id,
        user_context={}
    )
    print(f"Response 3:\n{response3}\n")
    
    print("="*80)
    print("Context window test complete!")
    print("="*80)


def test_tool_calling():
    """Test if agent calls tools appropriately"""
    thread_id = "test_tools_456"
    
    print("\n" + "="*80)
    print("TEST 2: Tool Calling (Check logs for 'Agent calling tools')")
    print("="*80)
    
    # This should trigger web_search
    print("\nMessage: 'What are the latest government schemes in 2026?'")
    response = run_agent(
        user_message="What are the latest government schemes in 2026?",
        thread_id=thread_id,
        user_context={}
    )
    print(f"Response:\n{response}\n")
    
    print("="*80)
    print("Tool calling test complete!")
    print("="*80)


def test_formatting():
    """Test if WhatsApp formatting is correct"""
    thread_id = "test_format_789"
    
    print("\n" + "="*80)
    print("TEST 3: Text Formatting (Check for **bold** or __italic__)")
    print("="*80)
    
    print("\nMessage: 'Tell me about PM-JAY eligibility'")
    response = run_agent(
        user_message="Tell me about PM-JAY eligibility",
        thread_id=thread_id,
        user_context={}
    )
    print(f"Response:\n{response}\n")
    
    # Check for markdown formatting issues
    if "**" in response or "__" in response:
        print("WARNING: Found double asterisks/underscores (markdown not normalized)")
    else:
        print("Text formatting looks good!")
    
    print("="*80)
    print("Formatting test complete!")
    print("="*80)


def test_simple_message():
    """Test a simple message"""
    thread_id = "test_simple_000"
    
    print("\n" + "="*80)
    print("TEST 4: Simple Message")
    print("="*80)
    
    print("\nMessage: 'Hello, what schemes can help me?'")
    response = run_agent(
        user_message="Hello, what schemes can help me?",
        thread_id=thread_id,
        user_context={}
    )
    print(f"Response:\n{response}\n")
    
    print("="*80)
    print("Simple message test complete!")
    print("="*80)


if __name__ == "__main__":
    print("\n")
    print("="*80)
    print("LOCAL AGENT TESTING (WITHOUT TWILIO)")
    print("Testing context window, tool calling, and text formatting")
    print("="*80)
    
    try:
        # Run all tests
        test_simple_message()
        test_context_window()
        test_tool_calling()
        test_formatting()
        
        print("\n" + "="*80)
        print("ALL TESTS COMPLETED!")
        print("="*80)
        print("\nNEXT STEPS:")
        print("1. Review logs above for any errors")
        print("2. Check if context is preserved across messages")
        print("3. Check if tools are being called (check logs for tool names)")
        print("4. Check if formatting is correct (no ** or __)")
        print("5. If all good, re-enable webhooks_twilio and test on WhatsApp")
        print("\n")
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        sys.exit(1)
