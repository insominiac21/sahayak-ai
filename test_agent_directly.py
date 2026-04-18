#!/usr/bin/env python3
"""Direct test of run_agent function with debugging"""
import sys
import os

# Add sarvamai/src to path so we can import from it
sys.path.insert(0, "sarvamai/src")

from app.services.agent.langgraph_agent import run_agent

# Test conversation simulation
def test_conversation():
    user_id = "test_user_123"
    
    print("\n" + "="*70)
    print("TEST 1: Ask about PM-JAY (should search and find info)")
    print("="*70)
    
    msg1 = "Tell me about PM-JAY scheme"
    response1 = run_agent(msg1, user_id)
    print(f"User: {msg1}")
    print(f"Agent: {response1}\n")
    
    print("="*70)
    print("TEST 2: Ask about income (should use conversation context)")
    print("="*70)
    
    msg2 = "My income is 5 lakhs, which category do I fall under?"
    response2 = run_agent(msg2, user_id)
    print(f"User: {msg2}")
    print(f"Agent: {response2}\n")
    
    print("="*70)
    print("TEST 3: Follow-up about eligibility")
    print("="*70)
    
    msg3 = "Am I eligible for PM-JAY?"
    response3 = run_agent(msg3, user_id)
    print(f"User: {msg3}")
    print(f"Agent: {response3}\n")

if __name__ == "__main__":
    print("Testing agent with conversation context...")
    test_conversation()
