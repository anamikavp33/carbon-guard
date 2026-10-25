from collections import defaultdict
from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from auth_utils import require_admin
from models.admin import (
    ActivityReport, AdminSubmissionDetail, AdminUserDetail, AdminUserRow, AuditLog, ConfigUpdate, CreditRule,
    CreditRuleUpdate, FraudFlag, MonthReport, Reports, ReviewAction, Stats, UserUpdate,
)
from models.common import ACTIVITY_TYPES, STATUSES, ActivityType, Page, SubmissionStatus
from models.submission import SubmissionSummary
from models.user import CreditTransaction, TrustEvent
from repositories import config_store, credit_rules, ledger, submissions, users
from repositories.helpers import now
from routes.views import counts_for_user, to_admin_detail, to_summary
from services import review

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------- submissions ----------------
@router.get("/submissions", response_model=Page[SubmissionSummary])
def list_submissions(status: Optional[SubmissionStatus] = None, activity_type: Optional[ActivityType] = None,
                     search: Optional[str] = Query(None, max_length=100, description="Part of the user's email"),
                     skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
                     admin: dict = Depends(require_admin)):
    rows, total = submissions.search(status, activity_type, search, skip, limit)
    return Page(items=[to_summary(r) for r in rows], total=total, skip=skip, limit=limit)


@router.get("/submissions/{submission_id}", response_model=AdminSubmissionDetail)
def submission_detail(submission_id: str, admin: dict = Depends(require_admin)):
    r = submissions.get(submission_id)
    if not r:
        raise HTTPException(status_code=404, detail="Submission not found")
    return to_admin_detail(r, users.get_by_id(r["user_id"]))


def _review(action, admin: dict, submission_id: str, body: Optional[ReviewAction]):
    try:
        r = action(admin, submission_id, body.notes if body else None)
    except LookupError:
        raise HTTPException(status_code=404, detail="Submission not found")
    except review.ReviewError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return to_admin_detail(r, users.get_by_id(r["user_id"]))


@router.post("/submissions/{submission_id}/approve", response_model=AdminSubmissionDetail)
def approve(submission_id: str, body: Optional[ReviewAction] = None, admin: dict = Depends(require_admin)):
    return _review(review.approve, admin, submission_id, body)


@router.post("/submissions/{submission_id}/reject", response_model=AdminSubmissionDetail)
def reject(submission_id: str, body: Optional[ReviewAction] = None, admin: dict = Depends(require_admin)):
    return _review(review.reject, admin, submission_id, body)


@router.post("/submissions/{submission_id}/manual-review", response_model=AdminSubmissionDetail)
def manual_review(submission_id: str, body: Optional[ReviewAction] = None, admin: dict = Depends(require_admin)):
    return _review(review.send_to_manual_review, admin, submission_id, body)


# ---------------- users ----------------
def _user_row(u: dict) -> AdminUserRow:
    return AdminUserRow(**{k: u.get(k, True if k == "is_active" else None) for k in AdminUserRow.model_fields})


@router.get("/users", response_model=Page[AdminUserRow])
def list_users(search: Optional[str] = Query(None, max_length=100, description="Part of a name or email"),
               skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
               admin: dict = Depends(require_admin)):
    rows, total = users.search(search, skip, limit)
    return Page(items=[_user_row(u) for u in rows], total=total, skip=skip, limit=limit)


def _user_detail(user_id: str) -> AdminUserDetail:
    u = users.get_by_id(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    recent, _ = submissions.list_for_user(user_id, 0, 20)
    return AdminUserDetail(
        **_user_row(u).model_dump(),
        submission_counts=counts_for_user(user_id),
        recent_submissions=[to_summary(r) for r in recent],
        trust_events=[TrustEvent(**e) for e in ledger.trust_events(user_id)],
        credit_transactions=[CreditTransaction(**t) for t in ledger.credit_transactions(user_id)],
    )


@router.get("/users/{user_id}", response_model=AdminUserDetail)
def user_detail(user_id: str, admin: dict = Depends(require_admin)):
    return _user_detail(user_id)


@router.patch("/users/{user_id}", response_model=AdminUserDetail)
def update_user(user_id: str, body: UserUpdate, admin: dict = Depends(require_admin)):
    u = users.get_by_id(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    if u["id"] == admin["id"] and not body.is_active:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account.")
    users.set_active(user_id, body.is_active)
    ledger.add_audit_log(admin, "user_activated" if body.is_active else "user_deactivated", "user", user_id)
    return _user_detail(user_id)


# ---------------- statistics and reports ----------------
@router.get("/stats", response_model=Stats)
def stats(admin: dict = Depends(require_admin)):
    by_status = {s: submissions.count({"status": s}) for s in STATUSES}
    verified = submissions.all_matching({"status": "verified"}, {"environmental_impact": 1})
    return Stats(
        total_users=users.count({"role": "user"}),
        active_users=users.count({"role": "user", "is_active": {"$ne": False}}),
        total_submissions=submissions.count(),
        by_status=by_status,
        by_activity={a: submissions.count({"activity_type": a}) for a in ACTIVITY_TYPES},
        awaiting_review=by_status["pending"] + by_status["manual_review"],
        total_credits_issued=ledger.total_credits_issued(),
        total_co2_estimate=round(sum((r["environmental_impact"]["co2_estimate"] or 0) for r in verified), 2),
        fraud_flagged=submissions.count({"fraud_check.flags.0": {"$exists": True}}),
    )


@router.get("/reports", response_model=Reports)
def reports(admin: dict = Depends(require_admin)):
    rows = submissions.all_matching({}, {"activity_type": 1, "status": 1, "green_credits_awarded": 1,
                                         "environmental_impact": 1, "created_at": 1})
    by_activity = []
    for a in ACTIVITY_TYPES:
        mine = [r for r in rows if r["activity_type"] == a]
        ver = [r for r in mine if r["status"] == "verified"]
        by_activity.append(ActivityReport(
            activity_type=a, submitted=len(mine), verified=len(ver),
            rejected=sum(1 for r in mine if r["status"] == "rejected"),
            credits_issued=round(sum(r["green_credits_awarded"] for r in ver), 2),
            co2_estimate_kg_per_year=round(sum((r["environmental_impact"]["co2_estimate"] or 0) for r in ver), 2),
        ))

    months = defaultdict(lambda: {"submitted": 0, "verified": 0, "credits_issued": 0.0})
    since = now() - timedelta(days=365)
    for r in rows:
        if r["created_at"] >= since:
            m = months[r["created_at"].strftime("%Y-%m")]
            m["submitted"] += 1
            if r["status"] == "verified":
                m["verified"] += 1
                m["credits_issued"] = round(m["credits_issued"] + r["green_credits_awarded"], 2)
    return Reports(
        by_activity=by_activity,
        by_month=[MonthReport(month=k, **v) for k, v in sorted(months.items())],
        note="CO2 figures are prototype estimates from this project's configurable factors, "
             "not certified carbon-offset measurements. Months are by submission date (UTC).",
    )


@router.get("/fraud-flags", response_model=Page[FraudFlag])
def fraud_flags(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
                admin: dict = Depends(require_admin)):
    logs, total = ledger.fraud_logs(skip, limit)
    items = []
    for log in logs:
        s = submissions.get(log["submission_id"])
        items.append(FraudFlag(
            id=log["id"], submission_id=log["submission_id"], user_id=log["user_id"],
            user_email=s["user_email"] if s else None, submission_status=s["status"] if s else None,
            flags=log["flags"], reasons=log["reasons"], related_submission_ids=log["related_submission_ids"],
            created_at=log["created_at"],
        ))
    return Page(items=items, total=total, skip=skip, limit=limit)


@router.get("/audit-logs", response_model=Page[AuditLog])
def audit_logs(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
               admin: dict = Depends(require_admin)):
    rows, total = ledger.audit_logs(skip, limit)
    return Page(items=[AuditLog(**r) for r in rows], total=total, skip=skip, limit=limit)


# ---------------- configurable rules ----------------
@router.get("/credit-rules", response_model=list[CreditRule])
def get_credit_rules(admin: dict = Depends(require_admin)):
    rules = credit_rules.all_rules()
    return [CreditRule(**rules[a]) for a in ACTIVITY_TYPES if a in rules]


@router.put("/credit-rules/{activity_type}", response_model=CreditRule)
def put_credit_rule(activity_type: str, rule: CreditRuleUpdate, admin: dict = Depends(require_admin)):
    if activity_type not in ACTIVITY_TYPES:
        raise HTTPException(status_code=404, detail="Unknown activity type")
    before = credit_rules.all_rules()[activity_type]
    after = credit_rules.update(activity_type, rule.model_dump(), admin["email"])
    ledger.add_audit_log(admin, "credit_rule_updated", "green_credit_rule", activity_type, {
        "before": {k: before[k] for k in ("base_credit_value", "impact_multiplier", "is_active")},
        "after": rule.model_dump(),
    })
    return CreditRule(**after)


@router.get("/config")
def get_config(admin: dict = Depends(require_admin)):
    return config_store.get()


@router.put("/config")
def put_config(update: ConfigUpdate, admin: dict = Depends(require_admin)):
    changes = update.model_dump(exclude_none=True)
    cur = config_store.get()
    for key in ("trust_rules", "impact_factors", "max_scale"):
        unknown = set(changes.get(key, {})) - set(cur[key])
        if unknown:
            raise HTTPException(status_code=400, detail=f"Unknown {key} keys: {sorted(unknown)}")
    new = config_store.update(changes)
    ledger.add_audit_log(admin, "config_updated", "settings", "verification", {"changes": changes})
    return new
