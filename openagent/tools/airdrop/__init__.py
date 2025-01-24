from pydantic import BaseModel


class AirdropAgentInput(BaseModel):
    wallet_address: str
    message: str


class AirdropAgentOutput(BaseModel):
    success: bool
    message: str
    airdrop_amount: float


__all__ = [
    "AirdropAgentInput",
    "AirdropAgentOutput",
]
