from fastapi import HTTPException, Request, Depends
from core.config import get_redis_client
import time

class RateLimiter:
    def __init__(self, times: int = 10, seconds: int = 60):
        self.times = times
        self.seconds = seconds

    async def __call__(self, request: Request, user: dict = Depends(lambda: {})):
        redis = get_redis_client()
        if not redis:
            return # Skip if redis not available

        # Identify user by ID if authenticated, else by IP
        user_id = user.get("id")
        if not user_id:
             user_id = request.client.host
        
        key = f"rate_limit:{request.url.path}:{user_id}"
        
        # Redis logic: increment counter, set expiry if new
        # Using a sliding window or fixed window. Fixed window is simpler.
        
        try:
            current = await redis.get(key)
            if current and int(current) >= self.times:
                ttl = await redis.ttl(key)
                raise HTTPException(
                    status_code=429, 
                    detail=f"Too many requests. Try again in {ttl} seconds."
                )
            pipe = redis.pipeline()
            pipe.incr(key, 1)
            if not current:
                pipe.expire(key, self.seconds)
            await pipe.execute()
        except Exception:
            return
