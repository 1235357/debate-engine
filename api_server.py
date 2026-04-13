#!/usr/bin/env python3
"""API server for DebateEngine using NVIDIA API."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from openai import OpenAI
import asyncio

app = FastAPI(
    title="DebateEngine API",
    description="Structured Multi-Agent Critique & Consensus Engine",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize NVIDIA API client
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
if not NVIDIA_API_KEY:
    raise RuntimeError("NVIDIA_API_KEY environment variable is required")

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY
)

class CritiqueRequest(BaseModel):
    content: str
    task_type: str = "CODE_REVIEW"

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[Message]
    model: str = "minimaxai/minimax-m2.7"

class StreamResponse(BaseModel):
    content: str
    finish_reason: str | None = None

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "model": "minimaxai/minimax-m2.7"}

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Chat endpoint using NVIDIA API."""
    try:
        # Convert messages to OpenAI format
        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
        ]
        
        completion = client.chat.completions.create(
            model=request.model,
            messages=openai_messages,
            temperature=1,
            top_p=0.95,
            max_tokens=8192
        )
        
        return {
            "content": completion.choices[0].message.content,
            "model": request.model
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/quick-critique")
async def quick_critique(request: CritiqueRequest):
    """Quick critique endpoint."""
    try:
        # System prompt for critique
        system_prompt = f"""You are a {request.task_type} expert. Analyze the following content and provide a detailed critique with specific issues, severity levels, and recommendations."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.content}
        ]
        
        completion = client.chat.completions.create(
            model="minimaxai/minimax-m2.7",
            messages=messages,
            temperature=0.7,
            top_p=0.9,
            max_tokens=4096
        )
        
        return {
            "critique": completion.choices[0].message.content,
            "task_type": request.task_type
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
