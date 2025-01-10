from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from .model import ChatCompletionRequest

router = APIRouter(tags=["Completion"])

@router.post("/chat/completions")
async def create_chat_completion(request: ChatCompletionRequest):
    pass

