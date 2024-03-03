from fastapi import APIRouter, Depends, Request
from typing import List
from schemas import AccidentSchema, InvalidateCacheRequest
from models import Accident 
from sqlalchemy.future import select
from utils import limiter
from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from custom_exceptions import DataNotFoundError, DatabaseConnectionError,  RedisConnectionError, AWSCredentialsError, CacheInvalidationError
from cache import get_cached_data, set_cache_data, redis_client
from redis.exceptions import RedisError
from security import api_key_auth
from fastapi.responses import JSONResponse
import logging
import os
import json

secure_router = APIRouter()
public_router = APIRouter()

logger = logging.getLogger(__name__)

@public_router.get("/accidents/", response_model=List[AccidentSchema])
@limiter.limit("10/minute")
async def read_accidents(request: Request, db: AsyncSession = Depends(get_db)):
    cache_key = "all_accidents"
    try:
        cached_accidents = await get_cached_data(cache_key)
        if cached_accidents:
            return json.loads(cached_accidents)
    except RedisConnectionError as e:
        # Log the Redis error or handle it as needed
        logger.exception(f"Redis connection error: {e}")

    try:
        async with db as session:
            query = select(Accident)
            result = await session.execute(query)
            accidents = result.scalars().all()
            
            if not accidents:
                raise DataNotFoundError(detail="Accidents not found")
            
            accidents_data = [accident.to_dict() for accident in accidents]
            

            # Serialize and cache the results before returning them
            await set_cache_data(
    cache_key,
    json.dumps(accidents_data),  # Assuming `to_dict` is a method on the `Accident` model
    expiration=60*60  # Cache for 1 hour
)

            return accidents_data

    except Exception as e:
        # This catches SQLAlchemy errors or any other unforeseen errors.
        raise DatabaseConnectionError(detail=str(e))

@public_router.get("/accidents/{accident_id}", response_model=AccidentSchema)
@limiter.limit("20/minute")
async def read_accident(request: Request, accident_id: int, db: AsyncSession = Depends(get_db)):
    cache_key = f"accident_{accident_id}"
    try:
        cached_accident = await get_cached_data(cache_key)
        if cached_accident:
            return json.loads(cached_accident)
    except RedisConnectionError as e:
        # Log the Redis error or handle it as needed
        logger.exception(f"Redis connection error: {e}")

    try:
        async with db as session:
            stmt = select(Accident).where(Accident.id == accident_id)
            result = await session.execute(stmt)
            accident = result.scalars().first()
            if not accident:
                raise DataNotFoundError(detail="Accident not found")

            # Serialize and cache the result before returning it
            await set_cache_data(cache_key, json.dumps(dict(accident)), expiration=60*60)  # Cache for 1 hour
            return accident

    except Exception as e:
        # This catches SQLAlchemy errors or any other unforeseen errors.
        raise DatabaseConnectionError(detail=str(e))
    
    
@public_router.get("/aws-credentials/")
@limiter.limit("10/minute")
async def get_aws_credentials(request: Request):
    cache_key = "aws_credentials"  # Define the cache key for AWS credentials

    try:
        # Attempt to retrieve the AWS credentials from cache
        cached_credentials = await get_cached_data(cache_key)
        if cached_credentials is not None:
            return JSONResponse(content=cached_credentials)
    except RedisConnectionError as e:
        # Log the Redis error or handle it as needed
        logger.exception(f"Redis connection error: {e}")

    # If credentials are not cached, fetch from environment variables
    identity_pool_id = os.environ.get("identity_pool_id")
    identity_pool_region = os.environ.get("identity_pool_region")
    map_name = os.environ.get("map_name")

    # Check if all required AWS credentials are available
    if not all([identity_pool_id, identity_pool_region, map_name]):
        # Raise an exception if AWS credentials are not properly configured
        raise AWSCredentialsError(detail="AWS credentials not configured properly.")

    # Prepare and return the AWS credentials
    aws_credentials = {
        "identityPoolId": identity_pool_id,
        "region": identity_pool_region,
        "mapName": map_name
    }

    # Cache the AWS credentials before returning
    await set_cache_data(cache_key, aws_credentials, expiration=60*60)  # Expires after 1 hour

    return JSONResponse(content=aws_credentials)


@secure_router.post("/invalidate-cache/")
async def invalidate_cache(request: InvalidateCacheRequest, api_key: str = Depends(api_key_auth)):
    try:
        if request.keys:
            # Invalidate specific cache keys
            for key in request.keys:
                await redis_client.delete(key)
        else:
            # Clear the entire cache (use with caution)
            await redis_client.flushdb()
        return {"message": "Cache invalidated successfully."}
    except RedisError as e:
        logger.exception(f"Redis error during cache invalidation: {e}")
        raise CacheInvalidationError()