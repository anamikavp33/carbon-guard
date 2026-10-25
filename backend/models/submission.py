from typing import Literal, Optional
from pydantic import BaseModel
from models.common import ActivityType, SubmissionStatus, UTCDateTime


class GPSLocation(BaseModel):
    lat: float
    lng: float
    accuracy_m: Optional[float] = None
    is_mocked: Optional[bool] = None


class AIVerification(BaseModel):
    status: Literal["available", "unavailable", "error"]
    model: Optional[str] = None
    predicted_class: Optional[str] = None
    confidence: Optional[float] = None
    matched: Optional[bool] = None
    scores: dict[str, float] = {}
    warnings: list[str] = []


class LocationVerification(BaseModel):
    gps_valid: bool
    accuracy_m: Optional[float] = None
    accuracy_ok: Optional[bool] = None
    address: Optional[str] = None
    geocoding_status: str
    notes: list[str] = []


class SatelliteVerification(BaseModel):
    status: Literal["not_configured", "available", "no_recent_image", "error", "skipped"]
    source: Optional[str] = None
    acquisition_date: Optional[str] = None
    cloud_cover: Optional[float] = None
    image_url: Optional[str] = None
    ndvi_mean: Optional[float] = None
    supports_claim: Optional[bool] = None
    notes: list[str] = []


class FraudCheck(BaseModel):
    is_duplicate_image: bool
    is_duplicate_location: bool
    suspicious_pattern: bool
    flags: list[str] = []
    reasons: list[str] = []


class EnvironmentalImpact(BaseModel):
    co2_estimate: Optional[float] = None
    unit: Optional[str] = None


class SubmissionStatusResponse(BaseModel):
    id: str
    status: SubmissionStatus
    updated_at: UTCDateTime


class SubmissionDetail(BaseModel):
    """What the owner of a submission sees. Admins get AdminSubmissionDetail (more fields)."""
    id: str
    activity_type: ActivityType
    status: SubmissionStatus
    image_url: str
    gps: GPSLocation
    description: Optional[str] = None
    scale_value: float
    ai_verification: Optional[AIVerification] = None            # null while processing
    location_verification: Optional[LocationVerification] = None
    satellite_verification: Optional[SatelliteVerification] = None
    fraud_check: Optional[FraudCheck] = None
    verification_score: Optional[float] = None
    score_components: dict[str, float] = {}
    decision_reasons: list[str] = []
    environmental_impact: EnvironmentalImpact
    green_credits_awarded: float
    review_notes: Optional[str] = None
    reviewed_at: Optional[UTCDateTime] = None
    created_at: UTCDateTime
    updated_at: UTCDateTime


class SubmissionSummary(BaseModel):
    """One row of a submission list."""
    id: str
    user_email: str
    activity_type: ActivityType
    status: SubmissionStatus
    image_url: str
    verification_score: Optional[float] = None
    flags: list[str] = []
    green_credits_awarded: float
    created_at: UTCDateTime
