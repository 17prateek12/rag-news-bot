import logging
from fastapi import Request, HTTPException, status
from app.core.redis_client import get_sync_redis

logger = logging.getLogger(__name__)


def rate_limit_login(request: Request):
    """
    FastAPI dependency to rate limit login requests.
    Allows 5 attempts per minute per IP address.
    """
    try:
        # Get client IP address
        ip = request.client.host if request.client else "unknown"
        # Redis key for this IP address
        key = f"rate_limit:login:{ip}"
        
        redis_client = get_sync_redis()
        # Increment the counter
        attempts = redis_client.incr(key)
        
        # If it is the first attempt, set TTL to 60 seconds
        if attempts == 1:
            redis_client.expire(key, 60)
            
        # If attempts exceed 5, raise 429 Too Many Requests
        if attempts > 5:
            logger.warning("Rate limit exceeded for IP %s on login endpoint", ip)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Please try again in a minute."
            )
    except HTTPException:
        raise
    except Exception as exc:
        # Fail closed: if Redis is unavailable, reject request to prevent brute-force attacks
        logger.error("Rate limiter Redis failure: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable. Please try again shortly.",
        )


def check_watch_update_rate_limit(user_id: object) -> None:
    """
    Rate limit watch updates (add / delete) to max 5 actions per day per user.
    """
    try:
        key = f"rate_limit:watch_update:{user_id}"
        redis_client = get_sync_redis()
        attempts = redis_client.incr(key)
        if attempts == 1:
            redis_client.expire(key, 86400)
        if attempts > 5:
            logger.warning("Watch update rate limit exceeded for user %s", user_id)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded: maximum 5 watch modifications allowed per day.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Rate limiter Redis failure on watch update: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rate limit service temporarily unavailable. Please try again shortly.",
        )

