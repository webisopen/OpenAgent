import binascii
import os
from datetime import UTC, datetime, timedelta

import jwt
from eth_account.messages import encode_defunct
from eth_utils import remove_0x_prefix, to_checksum_address
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from web3 import Web3

security = HTTPBearer(auto_error=False)


class Auth:
    def __init__(self):
        self.secret = os.getenv("JWT_SECRET_KEY", "your-secret-key")
        self.exp_time = 24 * 7

    def encode_token(self, wallet_address: str) -> str:
        payload = {
            "exp": datetime.now(UTC) + timedelta(hours=self.exp_time),
            "iat": datetime.now(UTC),
            "wallet_address": wallet_address.lower(),
        }
        return jwt.encode(payload, self.secret, algorithm="HS256")

    def decode_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, self.secret, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError as err:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
            ) from err
        except jwt.InvalidTokenError as err:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            ) from err

    def verify_wallet_signature(
        self, wallet_address: str, signature: str, nonce: str
    ) -> bool:
        try:
            message = f"Sign this message to authenticate with nonce: {nonce}"

            try:
                sig_bytes = bytes.fromhex(remove_0x_prefix(signature))
            except binascii.Error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid signature format",
                )

            if sig_bytes[64] >= 27:
                sig_bytes = sig_bytes[:64] + bytes([sig_bytes[64] - 27])

            w3 = Web3()
            recovered_address = w3.eth.account.recover_message(
                encode_defunct(text=message), signature=sig_bytes
            )

            return to_checksum_address(recovered_address) == to_checksum_address(
                wallet_address
            )

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Signature verification failed: {e!s}",
            )

    def auth_wrapper(
        self, auth: HTTPAuthorizationCredentials | None = Security(security)
    ) -> str:
        if not auth:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No authorization token provided",
                headers={"WWW-Authenticate": "Bearer"},
            )

        payload = self.decode_token(auth.credentials)
        return payload["wallet_address"]

    def optional_auth_wrapper(
        self, auth: HTTPAuthorizationCredentials | None = Security(security)
    ) -> str | None:
        if not auth:
            return None
        try:
            payload = self.decode_token(auth.credentials)
            return payload["wallet_address"]
        except HTTPException:
            return None
