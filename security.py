import re
import time
import uuid
from collections import defaultdict, deque
from threading import Lock
from typing import Deque

from fastapi import Depends, Header, HTTPException, Request, status

from config import settings


class InMemoryRateLimiter:
    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, Deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> None:
        now = time.time()
        window_start = now - self.window_seconds
        with self._lock:
            queue = self._hits[key]
            while queue and queue[0] < window_start:
                queue.popleft()
            if len(queue) >= self.limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        f"Rate limit exceeded: max {self.limit} requests in "
                        f"{self.window_seconds} seconds."
                    ),
                )
            queue.append(now)


rate_limiter = InMemoryRateLimiter(
    limit=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window_seconds,
)


def get_or_create_session_id(request: Request) -> str:
    session_id = request.cookies.get("session_id")
    if session_id:
        return session_id
    return str(uuid.uuid4())


def validate_sector_name(sector: str) -> str:
    cleaned = sector.strip().lower()
    if not cleaned:
        raise HTTPException(status_code=400, detail="Sector name cannot be empty.")
    if len(cleaned) > settings.max_sector_length:
        raise HTTPException(
            status_code=400,
            detail=f"Sector name too long. Max length is {settings.max_sector_length}.",
        )
    if not re.fullmatch(r"[a-zA-Z][a-zA-Z\s\-&]+", cleaned):
        raise HTTPException(
            status_code=400,
            detail="Sector name contains invalid characters.",
        )
    return cleaned


def verify_api_key(x_api_key: str = Header(default="")) -> None:
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )


def enforce_rate_limit(request: Request) -> str:
    session_id = get_or_create_session_id(request)
    rate_limiter.check(session_id)
    return session_id


AuthDependency = Depends(verify_api_key)
RateLimitDependency = Depends(enforce_rate_limit)
