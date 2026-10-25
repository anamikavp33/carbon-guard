"""Password hashing (bcrypt) and JWT access tokens (PyJWT)."""
from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from config import settings


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:   # malformed hash in the database
        return False


def create_access_token(user_id: str, role: str) -> tuple[str, int]:
    """Returns (token, lifetime in seconds). `sub` is the user id; the role is informational only:
    the backend re-reads the role from the database on every request."""
    lifetime = settings.JWT_EXPIRE_MINUTES * 60
    payload = {"sub": user_id, "role": role,
               "exp": datetime.now(timezone.utc) + timedelta(seconds=lifetime)}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM), lifetime


def decode_token(token: str) -> dict:
    """Raises jwt.InvalidTokenError (including expiry) for any bad token."""
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
