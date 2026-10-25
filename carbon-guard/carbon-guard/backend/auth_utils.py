"""FastAPI dependencies that identify the caller from the JWT token."""
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from bson import ObjectId
from repositories import users
from services.auth_service import decode_token

bearer_scheme = HTTPBearer(auto_error=False)

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not logged in or session expired. Please log in again.",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    if credentials is None:
        raise _UNAUTHORIZED
    try:
        user_id = decode_token(credentials.credentials).get("sub")
    except jwt.InvalidTokenError:
        raise _UNAUTHORIZED
    if not user_id or not ObjectId.is_valid(user_id):
        raise _UNAUTHORIZED
    user = users.get_by_id(user_id)
    if user is None:
        raise _UNAUTHORIZED
    if not user.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account has been deactivated.")
    return user


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    # The role is read from the database on every request, not trusted from the token.
    if current_user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user
