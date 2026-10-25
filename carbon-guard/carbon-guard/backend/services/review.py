"""Admin decisions. These are the ONLY places where credits are awarded and Trust Scores change.

  approve        : pending / manual_review -> verified   (+credits once, +trust)
  reject         : pending / manual_review -> rejected   (-trust; larger penalty if it was flagged)
  manual-review  : pending -> manual_review               (no trust change)
                   rejected -> manual_review              (reopens; refunds that rejection's penalty)

Every action is written to `audit_logs`.
"""
from repositories import config_store, ledger, submissions
from repositories.helpers import now
from services import credits, trust


class ReviewError(ValueError):
    pass


def _get(submission_id: str) -> dict:
    record = submissions.get(submission_id)
    if not record:
        raise LookupError("Submission not found")
    return record


def _move(record: dict, allowed: list, admin: dict, notes, changes: dict):
    if record["status"] not in allowed:
        raise ReviewError(f"Submission is '{record['status']}'; this action needs one of {allowed}.")
    t = now()
    ok = submissions.set_status_if(record["id"], allowed, {
        **changes, "reviewed_by": admin["email"], "review_notes": notes, "reviewed_at": t, "updated_at": t})
    if not ok:   # someone else changed it a moment ago
        raise ReviewError("The submission was changed by someone else. Reload and try again.")


def approve(admin: dict, submission_id: str, notes=None) -> dict:
    r = _get(submission_id)
    _move(r, ["pending", "manual_review"], admin, notes, {"status": "verified"})
    amount = credits.award_credits(r["user_id"], r)
    impact = credits.calculate_impact(r["activity_type"], r["scale_value"], config_store.get())
    submissions.update(r["id"], {"green_credits_awarded": amount, "environmental_impact": impact})
    trust.apply_event(r["user_id"], r["id"], "verified_submission", r["review_round"])
    ledger.add_audit_log(admin, "submission_approved", "submission", r["id"],
                         {"green_credits_awarded": amount, "notes": notes})
    return submissions.get(r["id"])


def reject(admin: dict, submission_id: str, notes=None) -> dict:
    r = _get(submission_id)
    _move(r, ["pending", "manual_review"], admin, notes, {"status": "rejected"})
    flagged = bool((r.get("fraud_check") or {}).get("flags"))
    event = "fraud_confirmed" if flagged else "rejected_submission"
    trust.apply_event(r["user_id"], r["id"], event, r["review_round"])
    ledger.add_audit_log(admin, "submission_rejected", "submission", r["id"], {"trust_event": event, "notes": notes})
    return submissions.get(r["id"])


def send_to_manual_review(admin: dict, submission_id: str, notes=None) -> dict:
    r = _get(submission_id)
    if r["status"] == "rejected":
        _move(r, ["rejected"], admin, notes, {"status": "manual_review", "review_round": r["review_round"] + 1})
        refunded = trust.refund_rejection(r["user_id"], r["id"], r["review_round"])
        details = {"reopened": True, "trust_refunded": refunded, "notes": notes}
    else:
        _move(r, ["pending"], admin, notes, {"status": "manual_review"})
        details = {"reopened": False, "notes": notes}
    ledger.add_audit_log(admin, "submission_sent_to_review", "submission", r["id"], details)
    return submissions.get(r["id"])
