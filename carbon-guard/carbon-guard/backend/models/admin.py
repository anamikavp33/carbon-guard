from typing import Optional
from pydantic import BaseModel, Field
from models.common import ActivityType, UTCDateTime
from models.submission import SubmissionDetail, SubmissionSummary
from models.user import CreditTransaction, SubmissionCounts, TrustEvent


class ReviewAction(BaseModel):
    notes: Optional[str] = Field(default=None, max_length=1000)


class AdminSubmissionDetail(SubmissionDetail):
    user_id: str
    user_email: str
    user_name: Optional[str] = None
    user_trust_score: Optional[float] = None
    related_submission_ids: list[str] = []
    image_hash: str
    review_round: int
    reviewed_by: Optional[str] = None
    processing_error: Optional[str] = None


class AdminUserRow(BaseModel):
    id: str
    name: str
    email: str
    role: str
    is_active: bool
    trust_score: float
    green_credits_total: float
    created_at: UTCDateTime


class AdminUserDetail(AdminUserRow):
    submission_counts: SubmissionCounts
    recent_submissions: list[SubmissionSummary]
    trust_events: list[TrustEvent]
    credit_transactions: list[CreditTransaction]


class UserUpdate(BaseModel):
    is_active: bool


class Stats(BaseModel):
    total_users: int
    active_users: int
    total_submissions: int
    by_status: dict[str, int]
    by_activity: dict[str, int]
    awaiting_review: int           # pending + manual_review
    total_credits_issued: float
    total_co2_estimate: float
    fraud_flagged: int


class ActivityReport(BaseModel):
    activity_type: ActivityType
    submitted: int
    verified: int
    rejected: int
    credits_issued: float
    co2_estimate_kg_per_year: float


class MonthReport(BaseModel):
    month: str          # "2026-10"
    submitted: int
    verified: int
    credits_issued: float


class Reports(BaseModel):
    by_activity: list[ActivityReport]
    by_month: list[MonthReport]
    note: str


class FraudFlag(BaseModel):
    id: str
    submission_id: str
    user_id: str
    user_email: Optional[str] = None
    submission_status: Optional[str] = None
    flags: list[str]
    reasons: list[str]
    related_submission_ids: list[str]
    created_at: UTCDateTime


class AuditLog(BaseModel):
    id: str
    admin_id: str
    admin_email: str
    action: str
    target_type: str
    target_id: str
    details: dict
    created_at: UTCDateTime


class CreditRule(BaseModel):
    activity_type: ActivityType
    base_credit_value: float
    impact_multiplier: float
    is_active: bool
    updated_by: Optional[str] = None
    updated_at: Optional[UTCDateTime] = None


class CreditRuleUpdate(BaseModel):
    base_credit_value: float = Field(ge=0, le=10000)
    impact_multiplier: float = Field(ge=0, le=100)
    is_active: bool = True


class WeightsUpdate(BaseModel):
    ai: float = Field(ge=0)
    gps: float = Field(ge=0)
    fraud: float = Field(ge=0)
    satellite: float = Field(ge=0)


class ConfigUpdate(BaseModel):
    """Every field is optional: send only what you want to change."""
    weights: Optional[WeightsUpdate] = None
    recommend_threshold: Optional[float] = Field(default=None, ge=0, le=100)
    ai_min_confidence: Optional[float] = Field(default=None, ge=0, le=1)
    gps_max_accuracy_m: Optional[float] = Field(default=None, gt=0)
    duplicate_location_radius_m: Optional[float] = Field(default=None, gt=0)
    similar_image_max_distance: Optional[int] = Field(default=None, ge=0, le=64)
    max_submissions_per_10min: Optional[int] = Field(default=None, ge=1)
    satellite_min_ndvi: Optional[float] = Field(default=None, ge=-1, le=1)
    max_scale: Optional[dict[str, float]] = None
    trust_rules: Optional[dict[str, float]] = None
    impact_factors: Optional[dict[str, float]] = None
