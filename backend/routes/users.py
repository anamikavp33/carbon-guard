from fastapi import APIRouter, Depends
from auth_utils import get_current_user
from models.user import CreditHistory, CreditTransaction, TrustEvent, TrustHistory, UserProfile
from repositories import config_store, ledger
from routes.views import co2_for_user, counts_for_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserProfile)
def my_profile(current_user: dict = Depends(get_current_user)):
    u = current_user
    return UserProfile(
        id=u["id"], name=u["name"], email=u["email"], role=u["role"],
        trust_score=u["trust_score"], green_credits_total=u["green_credits_total"],
        is_active=u.get("is_active", True), created_at=u["created_at"],
        submission_counts=counts_for_user(u["id"]), total_co2_estimate=co2_for_user(u["id"]),
    )


@router.get("/me/trust-history", response_model=TrustHistory)
def trust_history(current_user: dict = Depends(get_current_user)):
    cfg = config_store.get()
    return TrustHistory(
        trust_score=current_user["trust_score"], trust_min=cfg["trust_min"], trust_max=cfg["trust_max"],
        events=[TrustEvent(**e) for e in ledger.trust_events(current_user["id"])],
    )


@router.get("/me/credit-history", response_model=CreditHistory)
def credit_history(current_user: dict = Depends(get_current_user)):
    return CreditHistory(
        green_credits_total=current_user["green_credits_total"],
        transactions=[CreditTransaction(**t) for t in ledger.credit_transactions(current_user["id"])],
    )
