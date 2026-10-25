"""Turn database records into API response models (one place, so every route answers alike)."""
from models.admin import AdminSubmissionDetail
from models.submission import FraudCheck, SubmissionDetail, SubmissionSummary
from models.user import SubmissionCounts
from repositories import submissions
from repositories.helpers import to_oid


def _fraud_public(fraud):
    if fraud is None:
        return None
    return FraudCheck(**{k: v for k, v in fraud.items() if k != "related_submission_ids"})


def to_detail(r: dict) -> SubmissionDetail:
    return SubmissionDetail(
        **{k: r.get(k) for k in SubmissionDetail.model_fields if k not in ("fraud_check",)},
        fraud_check=_fraud_public(r.get("fraud_check")),
    )


def to_admin_detail(r: dict, user: dict = None) -> AdminSubmissionDetail:
    base = to_detail(r).model_dump()
    return AdminSubmissionDetail(
        **base,
        user_id=r["user_id"], user_email=r["user_email"],
        user_name=user["name"] if user else None,
        user_trust_score=user["trust_score"] if user else None,
        related_submission_ids=(r.get("fraud_check") or {}).get("related_submission_ids", []),
        image_hash=r["image_hash"], review_round=r.get("review_round", 0),
        reviewed_by=r.get("reviewed_by"), processing_error=r.get("processing_error"),
    )


def to_summary(r: dict) -> SubmissionSummary:
    return SubmissionSummary(
        id=r["id"], user_email=r["user_email"], activity_type=r["activity_type"], status=r["status"],
        image_url=r["image_url"], verification_score=r.get("verification_score"),
        flags=(r.get("fraud_check") or {}).get("flags", []),
        green_credits_awarded=r.get("green_credits_awarded", 0.0), created_at=r["created_at"],
    )


def counts_for_user(user_id: str) -> SubmissionCounts:
    rows = submissions.all_matching({"user_id": to_oid(user_id)}, {"status": 1})
    counts = SubmissionCounts(total=len(rows))
    for row in rows:
        setattr(counts, row["status"], getattr(counts, row["status"]) + 1)
    return counts


def co2_for_user(user_id: str) -> float:
    rows = submissions.all_matching({"user_id": to_oid(user_id), "status": "verified"}, {"environmental_impact": 1})
    return round(sum((r["environmental_impact"]["co2_estimate"] or 0) for r in rows), 2)
