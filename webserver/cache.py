from redis.asyncio import Redis
from redis.exceptions import RedisError  
from custom_exceptions import RedisConnectionError
import json
import os

# Initialize the Redis client asynchronously
redis_client = Redis(
    host=os.environ.get('REDIS_HOST'),
    port=os.environ.get('REDIS_PORT'),
    password=os.environ.get('REDIS_PASSWORD'),
    encoding="utf-8",
    decode_responses=True
)

async def get_cached_data(key):
    try:
        cached_data = await redis_client.get(key)
        return json.loads(cached_data) if cached_data else None
    except RedisError as e:  
        raise RedisConnectionError(detail=f"Redis error: {e}")

async def set_cache_data(key, data, expiration=60*60):
    try:
        await redis_client.setex(key, expiration, json.dumps(data))
    except RedisError as e:
        raise RedisConnectionError(detail=f"Redis error: {e}")