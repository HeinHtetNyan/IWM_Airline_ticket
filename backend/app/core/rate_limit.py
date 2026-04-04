import logging
from functools import lru_cache
from ipaddress import ip_address, ip_network
from typing import Iterable

from fastapi import HTTPException, Request

from backend.app.core.config import settings
from backend.app.core.redis import redis_client

logger = logging.getLogger(__name__)

_RATE_LIMIT_SCRIPT = redis_client.register_script(
    """
    local current = redis.call("INCR", KEYS[1])
    if current == 1 then
        redis.call("EXPIRE", KEYS[1], ARGV[1])
    end
    return current
    """
)


@lru_cache(maxsize=1)
def _trusted_proxy_networks() -> list:
    networks = []
    for raw_value in settings.TRUSTED_PROXY_CIDRS.split(","):
        cidr = raw_value.strip()
        if not cidr:
            continue
        try:
            networks.append(ip_network(cidr, strict=False))
        except ValueError:
            logger.warning("Ignoring invalid TRUSTED_PROXY_CIDRS entry: %s", cidr)
    return networks


def _is_trusted_proxy(host: str | None) -> bool:
    if not host:
        return False

    try:
        client_ip = ip_address(host)
    except ValueError:
        return False

    return any(client_ip in network for network in _trusted_proxy_networks())


def _forwarded_chain(request: Request) -> Iterable[str]:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    for raw_value in forwarded_for.split(","):
        host = raw_value.strip()
        if not host:
            continue
        try:
            ip_address(host)
        except ValueError:
            continue
        yield host


def _client_key(request: Request) -> str:
    peer_host = request.client.host if request.client else None
    if not _is_trusted_proxy(peer_host):
        return peer_host or "unknown"

    chain = [* _forwarded_chain(request), peer_host]
    for host in reversed(chain):
        if not _is_trusted_proxy(host):
            return host

    return peer_host or "unknown"


def enforce_rate_limit(
    request: Request,
    *,
    action: str,
    max_requests: int,
    window_seconds: int,
    fail_open: bool = True,
) -> None:
    key = f"{action}:{_client_key(request)}"
    redis_key = f"rate_limit:{key}"

    try:
        request_count = int(
            _RATE_LIMIT_SCRIPT(
                keys=[redis_key],
                args=[window_seconds],
            )
        )
    except Exception:
        if fail_open:
            logger.exception(
                "Rate limiter service unavailable (Redis error). Request allowed to prevent API disruption."
            )
            return
        logger.exception(
            "Rate limiter service unavailable (Redis error). Request denied for protected endpoint."
        )
        raise HTTPException(status_code=503, detail="Rate limit service unavailable. Please try again later.")

    if request_count > max_requests:
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")
