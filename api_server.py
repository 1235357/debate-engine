#!/usr/bin/env python3
"""API server for DebateEngine using NVIDIA API with multi-key support."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import os
import random
import time
import asyncio
from typing import List, Dict, Optional
from openai import OpenAI
from collections import defaultdict
import threading

app = FastAPI(
    title="DebateEngine API",
    description="Structured Multi-Agent Critique & Consensus Engine",
    version="0.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class APIKeyManager:
    """Manage multiple API keys with load balancing and failover."""
    
    def __init__(self, api_keys: List[str], base_url: str, model: str):
        self.api_keys = api_keys
        self.base_url = base_url
        self.model = model
        self.current_index = 0
        self.lock = threading.Lock()
        self.key_stats: Dict[str, dict] = defaultdict(lambda: {
            'success_count': 0,
            'failure_count': 0,
            'last_used': 0,
            'last_failed': 0,
            'is_active': True
        })
        self.cooldown_period = 60
        
    def get_next_key(self) -> str:
        """Get next API key using round-robin with failover."""
        with self.lock:
            start_index = self.current_index
            attempt = 0
            
            while attempt < len(self.api_keys):
                key = self.api_keys[self.current_index]
                self.current_index = (self.current_index + 1) % len(self.api_keys)
                
                stats = self.key_stats[key]
                now = time.time()
                
                if stats['is_active']:
                    if now - stats['last_failed'] > self.cooldown_period:
                        return key
                
                attempt += 1
            
            self.current_index = start_index
            return self.api_keys[start_index]
    
    def record_success(self, api_key: str):
        """Record a successful API call."""
        with self.lock:
            stats = self.key_stats[api_key]
            stats['success_count'] += 1
            stats['last_used'] = time.time()
            stats['is_active'] = True
    
    def record_failure(self, api_key: str):
        """Record a failed API call."""
        with self.lock:
            stats = self.key_stats[api_key]
            stats['failure_count'] += 1
            stats['last_failed'] = time.time()
            stats['is_active'] = False
    
    def get_stats(self) -> dict:
        """Get statistics about API key usage."""
        with self.lock:
            return {
                'total_keys': len(self.api_keys),
                'active_keys': sum(1 for k in self.api_keys if self.key_stats[k]['is_active']),
                'key_details': {
                    f'key_{i}': {
                        'success_count': self.key_stats[k]['success_count'],
                        'failure_count': self.key_stats[k]['failure_count'],
                        'is_active': self.key_stats[k]['is_active']
                    }
                    for i, k in enumerate(self.api_keys)
                }
            }


def load_api_keys() -> List[str]:
    """Load API keys from environment variables."""
    keys = []
    
    primary_key = os.getenv("NVIDIA_API_KEY")
    if primary_key:
        keys.append(primary_key)
    
    for i in range(1, 11):
        key = os.getenv(f"NVIDIA_API_KEY_{i}")
        if key:
            keys.append(key)
    
    if not keys:
        raise RuntimeError("At least one NVIDIA_API_KEY environment variable is required")
    
    return keys


BASE_URL = os.getenv("NVIDIA_API_BASE", "https://integrate.api.nvidia.com/v1")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "minimaxai/minimax-m2.7")

try:
    API_KEYS = load_api_keys()
    key_manager = APIKeyManager(API_KEYS, BASE_URL, DEFAULT_MODEL)
except Exception as e:
    print(f"Warning: {e}")
    key_manager = None


class CritiqueRequest(BaseModel):
    content: str
    task_type: str = "CODE_REVIEW"


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    model: str = DEFAULT_MODEL


class StreamResponse(BaseModel):
    content: str
    finish_reason: str | None = None


@app.get("/health")
async def health():
    """Health check endpoint."""
    stats = key_manager.get_stats() if key_manager else {}
    return {
        "status": "healthy",
        "model": DEFAULT_MODEL,
        "api_keys": stats
    }


@app.get("/api/stats")
async def get_stats():
    """Get API key usage statistics."""
    if not key_manager:
        raise HTTPException(status_code=500, detail="API key manager not initialized")
    return key_manager.get_stats()


async def make_api_call_with_retry(
    request: ChatRequest,
    stream: bool = False
):
    """Make API call with automatic retry on different keys."""
    if not key_manager:
        raise HTTPException(status_code=500, detail="API key manager not initialized")
    
    max_attempts = len(key_manager.api_keys) + 1
    last_exception = None
    
    for attempt in range(max_attempts):
        api_key = key_manager.get_next_key()
        
        try:
            client = OpenAI(
                base_url=key_manager.base_url,
                api_key=api_key
            )
            
            openai_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in request.messages
            ]
            
            completion = client.chat.completions.create(
                model=request.model,
                messages=openai_messages,
                temperature=1,
                top_p=0.95,
                max_tokens=8192,
                stream=stream
            )
            
            key_manager.record_success(api_key)
            return completion, api_key
            
        except Exception as e:
            key_manager.record_failure(api_key)
            last_exception = e
            await asyncio.sleep(0.5)
    
    raise HTTPException(
        status_code=500,
        detail=f"All API keys failed. Last error: {str(last_exception)}"
    )


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Chat endpoint using NVIDIA API with streaming and multi-key support."""
    try:
        completion, api_key = await make_api_call_with_retry(request, stream=True)
        
        async def stream_generator():
            for chunk in completion:
                if not getattr(chunk, "choices", None):
                    continue
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        
        return StreamingResponse(stream_generator(), media_type="text/plain")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/quick-critique")
async def quick_critique(request: CritiqueRequest):
    """Quick critique endpoint with multi-key support."""
    try:
        system_prompt = f"""You are a {request.task_type} expert. Analyze the following content and provide a detailed critique with specific issues, severity levels, and recommendations."""
        
        chat_request = ChatRequest(
            messages=[
                Message(role="system", content=system_prompt),
                Message(role="user", content=request.content)
            ],
            model=DEFAULT_MODEL
        )
        
        completion, api_key = await make_api_call_with_retry(chat_request, stream=False)
        
        return {
            "critique": completion.choices[0].message.content,
            "task_type": request.task_type,
            "api_key_used": f"key_{key_manager.api_keys.index(api_key)}" if key_manager else "unknown"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
