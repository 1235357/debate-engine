#!/usr/bin/env python3
"""Direct test of NVIDIA API using official example."""

import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

api_key = os.getenv("NVIDIA_API_KEY")

if not api_key:
    print("Error: NVIDIA_API_KEY not found in environment variables")
    exit(1)

print("Testing NVIDIA API directly with official example...")

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=api_key
)

try:
    completion = client.chat.completions.create(
        model="minimaxai/minimax-m2.7",
        messages=[{"role":"user","content":"Hello, please reply with 'OK'"}],
        temperature=1,
        top_p=0.95,
        max_tokens=8192,
        stream=False
    )
    
    print("\nSuccess!")
    print(f"Response: {completion.choices[0].message.content}")
    
except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()
