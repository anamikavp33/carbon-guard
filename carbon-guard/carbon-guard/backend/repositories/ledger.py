"""Credit transactions, trust score events, fraud logs and audit logs (append-only history)."""
from pymongo.errors import DuplicateKeyError
from database import get_db
from repositories.helpers import now, to_oid, with_id


def add_credit_transaction(user_id, submission_id, amount: float, rule_snapshot: dict) -> bool:
    """Returns False if this submission already received credits (idempotent)."""
    try:
        get_db().credit_transactions.insert_one({
            "user_id": to_oid(str(user_id)),
            "submission_id": to_oid(str(submission_id)),
            "type": "award",
            "amount": amount,
            "rule_snapshot": rule_snapshot,
            "created_at": now(),
        })
        return True
    except DuplicateKeyError:
        return False


def credit_transactions(user_id=None):
    query = {"user_id": to_oid(str(user_id))} if user_id else {}
    return [with_id(d) for d in get_db().credit_transactions.find(query).sort("created_at", -1)]


def total_credits_issued() -> float:
    return round(sum(d["amount"] for d in get_db().credit_transactions.find({}, {"amount": 1})), 2)


def add_trust_event(event_key: str, user_id, submission_id, event_type: str, delta: float,
                    reason: str, score_after: float) -> bool:
    """Returns False if an event with this key was already recorded (idempotent)."""
    try:
        get_db().trust_score_events.insert_one({
            "event_key": event_key,
            "user_id": to_oid(str(user_id)),
            "submission_id": to_oid(str(submission_id)) if submission_id else None,
            "event_type": event_type,
            "score_delta": delta,
            "reason": reason,
            "score_after": score_after,
            "created_at": now(),
        })
        return True
    except DuplicateKeyError:
        return False


def find_trust_event(event_key: str):
    return with_id(get_db().trust_score_events.find_one({"event_key": event_key}))


def trust_events(user_id=None):
    query = {"user_id": to_oid(str(user_id))} if user_id else {}
    return [with_id(d) for d in get_db().trust_score_events.find(query).sort("created_at", 1)]


def add_fraud_log(submission_id, user_id, flags: list, reasons: list, related_ids: list):
    get_db().fraud_logs.insert_one({
        "submission_id": to_oid(str(submission_id)),
        "user_id": to_oid(str(user_id)),
        "flags": flags,
        "reasons": reasons,
        "related_submission_ids": [to_oid(i) for i in related_ids],
        "created_at": now(),
    })


def fraud_logs(skip: int = 0, limit: int = 50):
    out = []
    for d in get_db().fraud_logs.find().sort("created_at", -1).skip(skip).limit(limit):
        d = with_id(d)
        d["related_submission_ids"] = [str(i) for i in d.get("related_submission_ids", [])]
        out.append(d)
    return out, get_db().fraud_logs.count_documents({})


def add_audit_log(admin: dict, action: str, target_type: str, target_id: str, details: dict = None):
    get_db().audit_logs.insert_one({
        "admin_id": to_oid(admin["id"]),
        "admin_email": admin["email"],
        "action": action,
        "target_type": target_type,
        "target_id": str(target_id),
        "details": details or {},
        "created_at": now(),
    })


def audit_logs(skip: int = 0, limit: int = 50):
    cur = get_db().audit_logs.find().sort("created_at", -1).skip(skip).limit(limit)
    out = []
    for d in cur:
        d = with_id(d)
        d["admin_id"] = str(d["admin_id"])
        out.append(d)
    return out, get_db().audit_logs.count_documents({})
