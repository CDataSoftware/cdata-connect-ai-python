"""
Authentication middleware for Basic Auth.
In Static Mode, any valid Basic Auth is accepted.
"""
import base64
from typing import Optional, Tuple

from fastapi import Header, HTTPException


def decode_basic_auth(authorization: str) -> Tuple[str, str]:
    """Decode Basic Auth header and return (username, password/token)."""
    if not authorization.startswith("Basic "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    try:
        encoded = authorization[6:]  # Remove "Basic "
        decoded = base64.b64decode(encoded).decode("utf-8")
        if ":" not in decoded:
            raise HTTPException(status_code=401, detail="Invalid credentials format")
        username, password = decoded.split(":", 1)
        return username, password
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid authorization header")


def get_auth_credentials(authorization: Optional[str] = Header(None)) -> Tuple[str, str]:
    """
    Dependency to extract and validate Basic Auth credentials.
    In Static Mode, any valid format is accepted.
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Basic"}
        )

    return decode_basic_auth(authorization)
