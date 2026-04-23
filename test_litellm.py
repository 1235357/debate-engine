import asyncio
from litellm import acompletion
import os

async def main():
    try:
        response = await acompletion(
            model="openai/minimaxai/minimax-m2.7",
            messages=[{"role": "user", "content": "Hello"}],
            api_base="https://integrate.api.nvidia.com/v1",
            api_key=os.environ.get("NVIDIA_API_KEY", "dummy"),
        )
        print("Success openai/: ", response.choices[0].message.content[:20])
    except Exception as e:
        print("Error openai/: ", e)

    try:
        response = await acompletion(
            model="nvidia_nim/minimaxai/minimax-m2.7",
            messages=[{"role": "user", "content": "Hello"}],
            api_base="https://integrate.api.nvidia.com/v1",
            api_key=os.environ.get("NVIDIA_API_KEY", "dummy"),
        )
        print("Success nvidia_nim/: ", response.choices[0].message.content[:20])
    except Exception as e:
        print("Error nvidia_nim/: ", e)

asyncio.run(main())
