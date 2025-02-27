from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from openagent.agent.agent import OpenAgent

# Create router
router = APIRouter(prefix="/chat", tags=["chat"])

# Store agent instance with type hint
agent_instance: Optional[OpenAgent] = None


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    content: str


# Chat endpoint
@router.post("", response_model=ChatResponse)
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
