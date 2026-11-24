"""Password hashing and JWT tokens.

Passwords are hashed with PBKDF2-HMAC-SHA256 (Python standard library) using
a random salt and 600,000 iterations. Plaintext passwords are never stored.
"""

import base64
import hashlib
import hmac
import logging
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import User
from app.models.enums import UserRole

logger = logging.getLogger(__name__)

PBKDF2_ITERATIONS = 600_000
DEMO_USER_EMAIL = "demo@agentforge.local"
GUEST_USER_EMAIL = "guest@agentforge.local"
# Built-in accounts that can never sign in with a password.
_SYSTEM_EMAILS = (DEMO_USER_EMAIL, GUEST_USER_EMAIL)
_ephemeral_secret: str | None = None


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    salt_b64 = base64.b64encode(salt).decode()
    digest_b64 = base64.b64encode(digest).decode()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt_b64}${digest_b64}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt_b64, digest_b64 = stored_hash.split("$")
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), base64.b64decode(salt_b64), int(iterations)
    )
    # compare_digest prevents timing attacks.
    return hmac.compare_digest(digest, base64.b64decode(digest_b64))


def _jwt_secret() -> str:
    global _ephemeral_secret
    settings = get_settings()
    if settings.jwt_secret:
        return settings.jwt_secret.get_secret_value()
    if settings.app_env == "production":
        raise RuntimeError("JWT_SECRET must be set when AUTH_ENABLED=true in production.")
    if _ephemeral_secret is None:
        logger.warning("JWT_SECRET not set: using a random per-process secret (dev only).")
        _ephemeral_secret = secrets.token_urlsafe(48)
    return _ephemeral_secret


def create_access_token(user: User) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user.id),
        "role": str(user.role),
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")


def decode_access_token(token: str) -> int | None:
    """Return the user id inside a valid token, or None if invalid/expired."""
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


def register_user(db: Session, name: str, email: str, password: str) -> User:
    """Create a user. The very first registered user becomes an admin."""
    existing = db.scalar(
        select(func.count(User.id)).where(User.email.not_in(_SYSTEM_EMAILS))) or 0
    is_first = existing == 0
    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role=UserRole.ADMIN if is_first else UserRole.MEMBER,
    )
    db.add(user)
    db.commit()
    return user


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None or user.email in _SYSTEM_EMAILS:
        # Still hash to keep response time similar for unknown emails.
        verify_password(password, hash_password("timing-equalizer"))
        return None
    return user if verify_password(password, user.password_hash) else None


def get_or_create_demo_user(db: Session) -> User:
    """Used only when AUTH_ENABLED=false. Its password is random and unusable."""
    user = db.scalar(select(User).where(User.email == DEMO_USER_EMAIL))
    if user is None:
        user = User(
            name="Demo User (auth disabled)",
            email=DEMO_USER_EMAIL,
            password_hash=hash_password(secrets.token_urlsafe(32)),
            role=UserRole.ADMIN,
        )
        db.add(user)
        db.commit()
    return user


def get_or_create_guest_user(db: Session) -> User:
    """Shared reviewer account behind the "Try the demo" button (DEMO_LOGIN_ENABLED).

    Reviewer, not admin: guests can run and approve workflows, nothing more.
    Its password is random and password login is refused for it.
    """
    user = db.scalar(select(User).where(User.email == GUEST_USER_EMAIL))
    if user is None:
        user = User(
            name="Guest Reviewer",
            email=GUEST_USER_EMAIL,
            password_hash=hash_password(secrets.token_urlsafe(32)),
            role=UserRole.REVIEWER,
        )
        db.add(user)
        db.commit()
    return user
