from collections import defaultdict, deque
from datetime import datetime, timezone
from threading import Lock

from fastapi import HTTPException, Request

_request_lock = Lock()
_request_history: dict[str, deque[datetime]] = defaultdict(deque)
_MAX_TRACKED_KEYS = 20_000


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(request: Request, *, action: str, max_requests: int, window_seconds: int) -> None:
    key = f"{action}:{_client_key(request)}"
    now = datetime.now(timezone.utc)

    with _request_lock:
        if len(_request_history) >= _MAX_TRACKED_KEYS and key not in _request_history:
            oldest_key = next(iter(_request_history))
            del _request_history[oldest_key]

        history = _request_history[key]
        while history and (now - history[0]).total_seconds() > window_seconds:
            history.popleft()

        if len(history) >= max_requests:
            raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")

        history.append(now)
