from typing import List

from fastapi import APIRouter, status
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

from openagent.agents import build_agent_team
from openagent.router.error import APIExceptionResponse

router = APIRouter(tags=["chat"])


class CreateChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatCompletionMessageParam]


@router.post("/chat/completions")
async def create_chat_completion(request: CreateChatCompletionRequest):
    try:
        agent_team = build_agent_team(request.model)
        agent_team.print_response(messages=request.messages)
    except Exception as error:
        return APIExceptionResponse(
            status_code=status.HTTP_400_BAD_REQUEST, error=error
        )
