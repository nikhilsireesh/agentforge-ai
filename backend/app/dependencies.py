"""Reusable FastAPI dependencies: current user, role checks, rate limiting."""

import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import User
from app.models.enums import UserRole
from app.services import auth_service

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Return the authenticated user, or the demo admin when auth is disabled."""
    if not get_settings().auth_enabled:
        return auth_service.get_or_create_demo_user(db)

    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required.")
    user_id = auth_service.decode_access_token(credentials.credentials)
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token.")
    return user


def require_roles(*roles: UserRole) -> Callable[..., User]:
    """Dependency factory: allow only users with one of the given roles."""

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"This action requires one of the roles: {', '.join(r.value for r in roles)}.",
            )
        return user

    return checker


require_reviewer = require_roles(UserRole.ADMIN, UserRole.REVIEWER)


class RateLimiter:
    """Simple in-memory sliding-window limiter (per client IP and bucket).

    Good enough for a single-process MVP; a multi-instance deployment would use Redis.
    """

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window_seconds: float = 60.0) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                return False
            hits.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


rate_limiter = RateLimiter()


def rate_limit(bucket: str) -> Callable[[Request], None]:
    def dependency(request: Request) -> None:
        client = request.client.host if request.client else "unknown"
        if not rate_limiter.check(f"{bucket}:{client}", get_settings().rate_limit_per_minute):
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS, "Rate limit exceeded. Try again in a minute."
            )

    return dependency
