"""Trust Score: a user-level reputation number between trust_min and trust_max (default 0-100).

It changes ONLY when an admin approves or rejects a submission, and every change is stored in
`trust_score_events` with a reason. Each event is keyed by submission + review round + event
type, so the same decision can never be counted twice.
"""
from repositories import config_store, ledger, users

REASONS = {
    "verified_submission": "An admin approved a submission.",
    "rejected_submission": "An admin rejected a submission.",
    "fraud_confirmed": "An admin rejected a submission that had been flagged for review.",
    "review_reopened": "A rejected submission was reopened for review (earlier penalty refunded).",
}


def _key(submission_id, review_round: int, event_type: str) -> str:
    return f"{submission_id}:{review_round}:{event_type}"


def _apply(user_id, submission_id, review_round: int, event_type: str, delta: float) -> float:
    cfg = config_store.get()
    user = users.get_by_id(user_id)
    old = user["trust_score"]
    new = round(min(cfg["trust_max"], max(cfg["trust_min"], old + delta)), 2)
    applied = round(new - old, 2)   # the real change after applying the bounds
    if ledger.add_trust_event(_key(submission_id, review_round, event_type), user_id, submission_id,
                              event_type, applied, REASONS[event_type], new):
        users.set_trust_score(user_id, new)
        return applied
    return 0.0   # this event was already applied


def apply_event(user_id, submission_id, event_type: str, review_round: int = 0) -> float:
    """Apply a configured rule (verified_submission / rejected_submission / fraud_confirmed)."""
    return _apply(user_id, submission_id, review_round, event_type,
                  config_store.get()["trust_rules"][event_type])


def refund_rejection(user_id, submission_id, review_round: int) -> float:
    """Undo exactly what the rejection in this review round took away (0 if it took nothing)."""
    for event_type in ("rejected_submission", "fraud_confirmed"):
        ev = ledger.find_trust_event(_key(submission_id, review_round, event_type))
        if ev and ev["score_delta"] < 0:
            return _apply(user_id, submission_id, review_round, "review_reopened", -ev["score_delta"])
    return 0.0
