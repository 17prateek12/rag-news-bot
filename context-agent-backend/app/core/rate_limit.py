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
        # Fail open: if Redis is down, log it and let the request proceed
        logger.error("Rate limiter encountered an error, failing open: %s", exc)
