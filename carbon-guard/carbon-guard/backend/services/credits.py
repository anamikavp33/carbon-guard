"""Green Credits: project-defined reward points. NOT legally recognised carbon credits."""
from repositories import credit_rules, ledger, users


def calculate_credits(activity_type: str, scale_value: float) -> tuple[float, dict]:
    rule = credit_rules.all_rules()[activity_type]
    if not rule["is_active"]:
        return 0.0, rule
    amount = round(rule["base_credit_value"] * rule["impact_multiplier"] * scale_value, 2)
    return amount, rule


def calculate_impact(activity_type: str, scale_value: float, cfg: dict) -> dict:
    factor = cfg["impact_factors"].get(activity_type, 0)
    return {"co2_estimate": round(factor * scale_value, 2), "unit": "kg_co2_per_year"}


def award_credits(user_id: str, submission: dict) -> float:
    """Give credits for a submission exactly once. Returns the amount actually awarded."""
    amount, rule = calculate_credits(submission["activity_type"], submission["scale_value"])
    snapshot = {k: rule[k] for k in ("base_credit_value", "impact_multiplier", "is_active")}
    if ledger.add_credit_transaction(user_id, submission["id"], amount, snapshot):
        users.add_credits(user_id, amount)
        return amount
    return 0.0   # already awarded earlier
