import logging

from fastapi import HTTPException

from backend.app.core.redis import redis_client

logger = logging.getLogger(__name__)


def build_rate_limit_key(action: str, identifier: str) -> str:
    return f"rate_limit:{action}:{identifier.strip().lower()}"


def check_rate_limit(key: str, limit: int, window: int, *, fail_open: bool = True) -> None:
    try:
        count = redis_client.incr(key)
        if count == 1:
            redis_client.expire(key, window)
    except Exception:
        if fail_open:
            logger.exception("Rate limiter unavailable for key %s. Allowing request.", key)
            return
        logger.exception("Rate limiter unavailable for key %s. Denying request.", key)
        raise HTTPException(status_code=503, detail="Rate limit service unavailable. Please try again later.")

    if count > limit:
        raise HTTPException(status_code=429, detail="Too many requests")


def enforce_email_rate_limit(
    action: str,
    email: str,
    limit: int,
    window: int,
    *,
    fail_open: bool = True,
) -> None:
    check_rate_limit(build_rate_limit_key(action, email), limit, window, fail_open=fail_open)
