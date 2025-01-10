import uuid
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ToolCall(BaseModel):
    id: str = Field(default_factory=lambda: f"call_{str(uuid.uuid4())}")
    type: str = "function"  # OpenAI currently only supports "function"
    function: Dict[str, Any]

class ChatFunctionCall(BaseModel):
    name: str
    arguments: str


class ChatMessage(BaseModel):
    role: str = Field(example="user")
    content: Optional[str] = Field(example="What's the current market situation for Bitcoin?")
    name: Optional[str] = Field(default=None, example=None)
    tool_calls: Optional[List[ToolCall]] = None
    function_call: Optional[ChatFunctionCall] = None


class ChatCompletionRequest(BaseModel):
    model: str = Field(example="llama3.2",description="The language model to use for the chat completion, e.g. 'qwen2', 'mistral', 'qwen2.5', 'llama3.1', 'llama3.2', 'mistral-nemo'")
    messages: List[ChatMessage] = Field(
        example=[
            {
                "role": "user",
                "content": "What's the current price of Ethereum and its market trend?"
            }
        ]
    )
    temperature: Optional[float] = Field(default=None, example=0.7)
    top_p: Optional[float] = Field(default=None, example=1.0)
    n: Optional[int] = Field(default=None, example=1)
    stream: Optional[bool] = Field(default=False, example=False)
    stop: Optional[List[str]] = Field(default=None, example=[])
    max_tokens: Optional[int] = Field(default=None, example=None)
    presence_penalty: Optional[float] = Field(default=None, example=0)
    frequency_penalty: Optional[float] = Field(default=None, example=0)
    user: Optional[str] = Field(default=None, example='oa')
