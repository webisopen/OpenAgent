from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from openagent.agent.agent import OpenAgent

# Create FastAPI app
app = FastAPI(title="OpenAgent API", description="API for OpenAgent", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store agent instance with type hint
agent_instance: Optional[OpenAgent] = None


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    content: str


# Chat endpoint
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    try:
        content = await agent_instance.chat(request.message)
        return ChatResponse(content=content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def set_agent(agent: OpenAgent):
    """Set the agent instance for the API

    Args:
        agent (OpenAgent): The agent instance to use
    """
    global agent_instance
    agent_instance = agent
