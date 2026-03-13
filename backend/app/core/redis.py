import redis

from backend.app.core.config import settings

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=False)
