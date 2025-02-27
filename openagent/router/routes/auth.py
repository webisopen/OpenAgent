from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, status
from loguru import logger

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
    logger.info(f"Login attempt from wallet: {wallet_address}")
    logger.debug(f"Received signature length: {len(signature)}")
    logger.debug(f"Received nonce: {nonce}")

    try:
        if auth_handler.verify_wallet_signature(wallet_address, signature, nonce):
            logger.info(
                f"Signature verification successful for wallet: {wallet_address}"
            )
            try:
                token = auth_handler.encode_token(wallet_address)
                logger.info(
                    f"Successfully generated token for wallet: {wallet_address}"
                )
                return ResponseModel(
                    code=status.HTTP_200_OK,
                    message="Login successful",
                    data=AuthResponse(token=token, wallet_address=wallet_address),
                )
            except Exception as e:
                logger.error(f"Failed to encode token: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Token generation failed: {str(e)}",
                )
        logger.warning(f"Invalid signature for wallet: {wallet_address}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature"
        )
    except HTTPException:
        # Re-raise HTTPExceptions
        raise
    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"Unexpected error during login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}",
        )
