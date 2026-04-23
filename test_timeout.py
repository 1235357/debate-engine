import asyncio
import os
from litellm import acompletion
import logging

import litellm
litellm.set_verbose = True

async def main():
    try:
        response = await asyncio.wait_for(
            acompletion(
                model="openai/minimaxai/minimax-m2.7",
                messages=[{"role": "user", "content": "Hello, are you there?"}],
                api_base="https://integrate.api.nvidia.com/v1",
                api_key=os.environ.get("NVIDIA_API_KEY", "dummy_key"),
                max_tokens=100
            ),
            timeout=10.0
        )
        print("Response:", response)
    except Exception as e:
        print("Error:", e)

asyncio.run(main())
