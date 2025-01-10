import time
import uuid
from typing import List, Union

from fastapi import APIRouter, status
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletion,
    ChatCompletionMessage,
)
from openai.types.chat.chat_completion import Choice
from pydantic import BaseModel

from openagent.agents import build_agent_team
from openagent.router.error import APIExceptionResponse

router = APIRouter(tags=["chat"])


class CreateChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatCompletionMessageParam]


@router.post(
    "/v1/chat/completions", response_model=None, response_model_exclude_none=True
)
async def create_chat_completion(
    request: CreateChatCompletionRequest,
) -> Union[ChatCompletion, APIExceptionResponse]:
    try:
        agent_team = build_agent_team(request.model)
        result = agent_team.run(messages=request.messages)

        return ChatCompletion(
            id=str(uuid.uuid4()),
            created=int(time.time()),
            model=request.model,
            object="chat.completion",
            choices=[
                Choice(
                    message=ChatCompletionMessage(
                        role="assistant", content=result.content
                    ),
                    finish_reason="stop",
                    index=0,
                )
            ],
        )
    except Exception as error:
        return APIExceptionResponse(
            status_code=status.HTTP_400_BAD_REQUEST, error=error
        )
