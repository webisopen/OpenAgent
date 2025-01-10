from phi.agent import Agent
from phi.model.base import Model
from phi.model.ollama import Ollama
from phi.model.openai import OpenAIChat
from phi.model.anthropic import Claude
from phi.model.google import Gemini

from .finance import finance_agent


class UnsupportedModel(Exception):
    def __init__(self, model: str):
        self.model = model

    def __str__(self):
        return f"Unsupported model {self.model}"


def build_model(model: str) -> Model:
    (provider, model_id) = model.split("/")

    match provider:
        case "openai":
            return OpenAIChat(id=model_id)
        case "anthropic":
            return Claude(id=model_id)
        case "google":
            return Gemini(id=model_id)
        case "ollama":
            return Ollama(id=model_id)
        case _:
            raise UnsupportedModel(model)


def build_agent_team(model: str) -> Agent:
    return Agent(
        team=[finance_agent],
        model=build_model(model),
    )


__all__ = [build_agent_team]
