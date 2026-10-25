from typing import Literal, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
from models.common import UTCDateTime


class UserRegister(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=64)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be blank")
        return v.strip()

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("password is too long")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int          # seconds until the token expires


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: Literal["user", "admin"]


class SubmissionCounts(BaseModel):
    total: int = 0
    processing: int = 0
    pending: int = 0
    manual_review: int = 0
    verified: int = 0
    rejected: int = 0


class UserProfile(UserResponse):
    trust_score: float
    green_credits_total: float
    is_active: bool
    created_at: UTCDateTime
    submission_counts: SubmissionCounts
    total_co2_estimate: float


class CreditTransaction(BaseModel):
    id: str
    submission_id: str
    type: str
    amount: float
    created_at: UTCDateTime


class CreditHistory(BaseModel):
    green_credits_total: float
    transactions: list[CreditTransaction]


class TrustEvent(BaseModel):
    id: str
    submission_id: Optional[str] = None
    event_type: str
    score_delta: float
    score_after: float
    reason: str
    created_at: UTCDateTime


class TrustHistory(BaseModel):
    trust_score: float
    trust_min: float
    trust_max: float
    events: list[TrustEvent]
