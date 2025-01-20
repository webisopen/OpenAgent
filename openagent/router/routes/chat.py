import time
import uuid
from typing import Union
from fastapi import APIRouter, status
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionMessage,
)
from openai.types.chat.chat_completion import Choice
from openagent.agents import build_agent_team
from openagent.router.error import APIExceptionResponse
from openagent.router.routes.models.request import CreateChatCompletionRequest

router = APIRouter(tags=["chat"])


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
