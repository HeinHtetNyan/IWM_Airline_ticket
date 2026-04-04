import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.auth_token import AuthToken

VERIFY_EMAIL = "VERIFY_EMAIL"
RESET_PASSWORD = "RESET_PASSWORD"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def create_auth_token(
    db: Session,
    *,
    user_id,
    token_type: str,
    expires_minutes: int,
) -> str:
    raw_token = secrets.token_urlsafe(48)
    token_record = AuthToken(
        user_id=user_id,
        token_hash=hash_token(raw_token),
        type=token_type,
        expires_at=utc_now() + timedelta(minutes=expires_minutes),
        used=False,
    )
    db.add(token_record)
    db.commit()
    db.refresh(token_record)
    return raw_token


def create_email_verification_token(db: Session, *, user_id) -> str:
    return create_auth_token(
        db,
        user_id=user_id,
        token_type=VERIFY_EMAIL,
        expires_minutes=settings.TOKEN_EXPIRE_MINUTES_VERIFY,
    )


def create_password_reset_token(db: Session, *, user_id) -> str:
    return create_auth_token(
        db,
        user_id=user_id,
        token_type=RESET_PASSWORD,
        expires_minutes=settings.TOKEN_EXPIRE_MINUTES_RESET,
    )


def get_valid_auth_token(db: Session, *, raw_token: str, token_type: str) -> AuthToken:
    token_hash = hash_token(raw_token)
    token_record = (
        db.query(AuthToken)
        .filter(
            AuthToken.token_hash == token_hash,
            AuthToken.type == token_type,
            AuthToken.used == False,  # noqa: E712
        )
        .first()
    )
    if token_record is None:
        raise HTTPException(status_code=400, detail="Invalid or already used token")

    if _ensure_utc(token_record.expires_at) <= utc_now():
        raise HTTPException(status_code=400, detail="Token has expired")

    return token_record


def mark_token_used(db: Session, token_record: AuthToken) -> None:
    token_record.used = True
    db.add(token_record)
    db.commit()
