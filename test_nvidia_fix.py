#!/usr/bin/env python3
"""Test script to verify NVIDIA API fix."""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from debate_engine.providers.llm_provider import LLMProvider
from debate_engine.providers.config import ProviderConfig


async def test_nvidia_api():
    """Test NVIDIA API call with the fixed configuration."""
    print("Testing NVIDIA API fix...")
    
    # Create config
    config = ProviderConfig.from_env()
    print(f"Provider: {config.primary_provider}")
    print(f"Model: {config.primary_model}")
    print(f"API Base: {config.primary_api_base}")
    
    # Create provider
    provider = LLMProvider(config)
    
    # Test with simple message
    messages = [{"role": "user", "content": "Hello, please reply with 'OK'"}]
    
    try:
        result, call_result = await provider.call(
            messages=messages,
            temperature=0.7
        )
        print(f"\nSuccess!")
        print(f"Response: {result}")
        print(f"Status: {call_result.status}")
        print(f"Model used: {call_result.model_used}")
        print(f"Cost: ${call_result.cost_usd:.6f}")
        print(f"Latency: {call_result.latency_ms:.0f}ms")
        return True
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import asyncio
    success = asyncio.run(test_nvidia_api())
    sys.exit(0 if success else 1)
