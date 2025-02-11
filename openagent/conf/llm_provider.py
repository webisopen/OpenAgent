from typing import Dict, List

import ollama
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_vertexai import ChatVertexAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from loguru import logger
from toolz import memoize

from openagent.conf.env import settings

SUPPORTED_OLLAMA_MODELS = {
    "llama3.2": {"name": "llama3.2", "supports_tools": True},
    "darkmoon/olmo:7B-instruct-q6-k": {"name": "olmo", "supports_tools": False},
    'llama3.1': {'name': 'llama3.1', 'supports_tools': True},
    "qwen2.5": {"name": "qwen2.5", "supports_tools": True},
    "mistral": {"name": "mistral", "supports_tools": True},
    "deepseek-r1:32b": {"name": "deepseek-r1", "supports_tools": False},
}

MODELS_ICONS = {
    "llama3.1": "/public/llama.png",
    "llama3.2": "/public/llama.png",
    "mistral": "/public/mistral.png",
    "mistral-nemo": "/public/mistral.png",
    "mistral-large": "/public/mistral.png",
    "olmo": "/public/olmo.png",
    "qwen2": "/public/qwen.png",
    "qwen2.5": "/public/qwen.png",
    "deepseek-r1":"public/deepseek.png",
}


@memoize
def get_available_ollama_providers() -> List[str]:
    try:
        ollama_list = ollama.list()
        available_models = []
        for model in ollama_list["models"]:
            full_name = model["name"]
            # check if the full model name is in SUPPORTED_MODELS
            if full_name in SUPPORTED_OLLAMA_MODELS:
                available_models.append(full_name)
            else:
                # try to check the base name (without version tag)
                base_name = full_name.split(":")[0]
                if base_name in SUPPORTED_OLLAMA_MODELS:
                    available_models.append(base_name)
        return available_models
    except Exception as e:
        logger.exception("Failed to get available ollama providers", e)
        return []


def get_provider(model: str, provider_func) -> Dict[str, BaseChatModel]:
    provider = provider_func(model)
    return {model: provider} if provider else {}


def get_available_providers() -> Dict[str, BaseChatModel]:
    providers = {}

    provider_configs = [
        (["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"], get_openai_provider),
        (["claude-3-5-sonnet"], get_anthropic_provider),
        (["gemini-1.5-pro", "gemini-1.5-flash"], get_gemini_provider),
    ]

    for models, provider_func in provider_configs:
        for model in models:
            providers.update(get_provider(model, provider_func))

    if settings.OLLAMA_HOST:
        ollama_models = get_available_ollama_providers()
        for model in ollama_models:
            providers.update(get_provider(model, get_ollama_provider))

    return providers


def get_openai_provider(model: str) -> BaseChatModel | None:
    return ChatOpenAI(model=model) if settings.OPENAI_API_KEY else None


def get_anthropic_provider(model: str) -> BaseChatModel | None:
    return ChatAnthropic(model="claude-3-5-sonnet-20240620", ) if settings.ANTHROPIC_API_KEY else None


def get_gemini_provider(model: str) -> BaseChatModel | None:
    if settings.VERTEX_PROJECT_ID:
        return ChatVertexAI(model=model)
    elif settings.GOOGLE_GEMINI_API_KEY:
        return ChatGoogleGenerativeAI(model=model, google_api_key=settings.GOOGLE_GEMINI_API_KEY)
    return None


def get_ollama_provider(model: str) -> BaseChatModel | None:
    return ChatOllama(model=model) if settings.OLLAMA_HOST else None
