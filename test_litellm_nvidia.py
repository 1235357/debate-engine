#!/usr/bin/env python3
"""Test LiteLLM with NVIDIA API."""

import os
import asyncio
from dotenv import load_dotenv
import litellm

# Load environment variables
load_dotenv()

api_key = os.getenv("NVIDIA_API_KEY")

if not api_key:
    print("Error: NVIDIA_API_KEY not found in environment variables")
    exit(1)

print("Testing LiteLLM with NVIDIA API...")

async def test_different_formats():
    """Test different model formats."""
    
    test_cases = [
        # Test 1: Direct model name with custom_llm_provider
        {
            "name": "Direct model with custom_llm_provider=openai",
            "model": "minimaxai/minimax-m2.7",
            "api_base": "https://integrate.api.nvidia.com/v1",
            "custom_llm_provider": "openai",
        },
        # Test 2: nvidia/ prefix
        {
            "name": "nvidia/ prefix",
            "model": "nvidia/minimaxai/minimax-m2.7",
            "api_base": "https://integrate.api.nvidia.com/v1",
        },
        # Test 3: Just model name (no prefix)
        {
            "name": "Just model name",
            "model": "minimaxai/minimax-m2.7",
            "api_base": "https://integrate.api.nvidia.com/v1",
        },
    ]
    
    for test in test_cases:
        print(f"\n{'='*60}")
        print(f"Testing: {test['name']}")
        print(f"{'='*60}")
        
        try:
            # Build params
            params = {
                "model": test["model"],
                "messages": [{"role": "user", "content": "Hello, reply with 'OK'"}],
                "api_key": api_key,
                "api_base": test["api_base"],
            }
            
            if "custom_llm_provider" in test:
                params["custom_llm_provider"] = test["custom_llm_provider"]
            
            response = await litellm.acompletion(**params)
            print(f"✓ Success!")
            print(f"Response: {response.choices[0].message.content}")
            
        except Exception as e:
            print(f"✗ Error: {e}")

asyncio.run(test_different_formats())
