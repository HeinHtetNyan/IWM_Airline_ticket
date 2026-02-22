import redis
from fastapi import Depends
import os

redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_client = redis.from_url(redis_url, decode_responses=True)

def get_redis():
    return redis_client