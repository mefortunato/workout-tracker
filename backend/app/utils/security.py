"""Shared security helpers: rate limiting, auth cookies, and regex escaping."""
import re
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Deque, Dict

from fastapi import HTTPException, Request, Response, status

from app.config import settings

AUTH_COOKIE_NAME = "access_token"
OAUTH_STATE_COOKIE_NAME = "oauth_state"

# Header the SPA sends on every request. Browsers do not allow cross-site forms to
# set custom headers, and cross-origin fetches that set one need a CORS preflight
# that only allowed origins pass, so requiring it blocks CSRF on cookie sessions.
CSRF_HEADER_NAME = "X-Requested-With"


def get_client_ip(request: Request) -> str:
    if settings.TRUST_PROXY_HEADERS:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            # The right-most entry is the one appended by the trusted proxy.
            return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


class RateLimiter:
    """In-memory sliding-window limiter.

    State is per process, so with several instances the effective limit is
    multiplied by the instance count. Use a shared store (e.g. Redis) for strict limits.
    """

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def hit(self, key: str) -> bool:
        """Records a hit for `key` and returns False if the limit is exceeded."""
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] < cutoff:
                hits.popleft()
            if len(hits) >= self.max_requests:
                return False
            hits.append(now)
            if len(self._hits) > 50_000:
                # Bound memory: drop keys whose windows have fully expired.
                for k in [k for k, v in self._hits.items() if not v or v[-1] < cutoff]:
                    del self._hits[k]
            return True

    def check(self, *keys: str) -> None:
        for key in keys:
            if not self.hit(key):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many attempts. Please wait a minute and try again.",
                    headers={"Retry-After": str(self.window_seconds)},
                )

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


auth_limiter = RateLimiter(settings.AUTH_RATE_LIMIT, settings.AUTH_RATE_WINDOW_SECONDS)
join_limiter = RateLimiter(settings.AUTH_RATE_LIMIT, settings.AUTH_RATE_WINDOW_SECONDS)


def set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


def exact_name_regex(name: str) -> Dict[str, str]:
    """Case-insensitive exact-match Mongo regex with user input escaped."""
    return {"$regex": f"^{re.escape(name.strip())}$", "$options": "i"}
