from openagent.tools import BaseTool
from openagent.tools.airdrop import AirdropAgentInput, AirdropAgentOutput
from phi.model.base import Model


class AirdropAgent(BaseTool):
    def __init__(self, model: Model | None = None):
        super().__init__(name="airdrop_agent", model=model)

    def run(self, input: AirdropAgentInput) -> tuple[bool, AirdropAgentOutput]:
        pass

    def generate_airdrop_output(self, input: AirdropAgentInput) -> tuple[bool, str]:
        pass
