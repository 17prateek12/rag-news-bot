import logging
from fastapi import Request, HTTPException, status
from app.core.redis_client import get_sync_redis

logger = logging.getLogger(__name__)


def rate_limit_login(request: Request):
    """
    FastAPI dependency to rate limit login/register requests.
    Allows 5 attempts per minute per IP address.
    M-1: Fails CLOSED — if Redis is unavailable, the request is rejected (HTTP 503)
    rather than silently allowed through, preventing brute-force during outages.
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
        # M-1: Fail CLOSED — reject the request so brute-force protection is never bypassed
        logger.error("Rate limiter Redis error, failing closed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable. Please try again shortly.",
        )


def check_watch_update_rate_limit(user_id, max_updates: int = 5) -> None:
    """
    Check and increment the daily watch modification counter for a user (adds + deletes).
    Limits users to max 5 watch modifications per day to prevent abuse and excessive LLM calls.
    """
    try:
        from datetime import datetime, timezone
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        key = f"rate_limit:watches:{user_id}:{today_str}"

        redis_client = get_sync_redis()
        count = redis_client.incr(key)

        # Set 24h TTL on first action of the day
        if count == 1:
            redis_client.expire(key, 86400)

        if count > max_updates:
            logger.warning(
                "Daily watch modification limit exceeded for user %s (%s/%s)",
                user_id,
                count,
                max_updates,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Daily watch modification limit reached ({max_updates} changes allowed per day). Please try again tomorrow.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Watch rate limiter Redis error, failing closed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Topic watch service temporarily unavailable. Please try again shortly.",
        )

