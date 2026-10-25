from fastapi import APIRouter, Depends, HTTPException
from auth_utils import get_current_user
from models.user import Token, UserLogin, UserRegister, UserResponse
from repositories import config_store, users
from services.auth_service import create_access_token, hash_password, verify_password
from services.rate_limit import auth_rate_limit

router = APIRouter(prefix="/auth", tags=["auth"])


def public_user(u: dict) -> UserResponse:
    return UserResponse(id=u["id"], name=u["name"], email=u["email"], role=u["role"])


@router.post("/register", response_model=UserResponse, status_code=201, dependencies=[Depends(auth_rate_limit)])
def register(user: UserRegister):
    # Anyone can register, but only as a normal user. Admins are created by the seed step.
    created = users.create(user.name, user.email, hash_password(user.password), role="user",
                           trust_score=config_store.get()["trust_initial"])
    if created is None:
        raise HTTPException(status_code=400, detail="Email already registered")
    return public_user(created)


@router.post("/login", response_model=Token, dependencies=[Depends(auth_rate_limit)])
def login(credentials: UserLogin):
    user = users.get_by_email(credentials.email)
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="This account has been deactivated.")
    token, lifetime = create_access_token(user["id"], user["role"])
    return Token(access_token=token, expires_in=lifetime)


@router.get("/me", response_model=UserResponse)
def me(current_user: dict = Depends(get_current_user)):
    return public_user(current_user)
