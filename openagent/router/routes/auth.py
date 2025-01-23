from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, status

from openagent.router.routes.models.auth import Auth
from openagent.router.routes.models.response import AuthResponse, ResponseModel

router = APIRouter(prefix="/auth", tags=["auth"])
auth_handler = Auth()


@router.post(
    "/login",
    response_model=ResponseModel[AuthResponse],
    summary="Login with wallet",
    description="Authenticate user using wallet address, signature and nonce. Returns a JWT token upon successful authentication.",
    responses={
        200: {"description": "Successfully authenticated"},
        401: {"description": "Authentication failed"},
        500: {"description": "Internal server error"},
    },
)
def login(
    wallet_address: Annotated[str, Header()],
    signature: Annotated[str, Header()],
    nonce: Annotated[str, Header()],
) -> ResponseModel:
    if auth_handler.verify_wallet_signature(wallet_address, signature, nonce):
        token = auth_handler.encode_token(wallet_address)
        return ResponseModel(
            code=status.HTTP_200_OK,
            message="Login successful",
            data=AuthResponse(token=token, wallet_address=wallet_address),
        )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature"
    )
