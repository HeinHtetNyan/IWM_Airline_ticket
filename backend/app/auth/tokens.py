from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError

from backend.app.core.config import settings


class TokenExpiredError(JWTError):
    """Raised when an access token is structurally valid but expired."""


def create_access_token(subject: str, role: str, expires_minutes: Optional[int] = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode: Dict[str, Any] = {
        "sub": subject,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except ExpiredSignatureError as exc:
        raise TokenExpiredError("Token has expired") from exc
