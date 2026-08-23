"""Waitlist confirmation banding: >70 confirm, 30-70 probable, <30 low.
RAC and AVAILABLE both count as confirmed. Pure Python -- no FastAPI, no
OpenAI, no ORM imports."""

from app.dataset import WAITLIST_QUOTAS_BY_QUOTA
from app.models import WaitlistPrediction

CONFIRM_THRESHOLD = 70.0
LOW_THRESHOLD = 30.0


def predict(status: str, quota: str, position: int) -> WaitlistPrediction:
    if status == "RAC":
        return WaitlistPrediction(
            band="confirm",
            probability=100.0,
            waitlist_type=f"{quota}RAC",
            position=position,
            explanation="RAC counts as confirmed -- you'd get a seat, just shared.",
        )
    if status == "AVAILABLE":
        return WaitlistPrediction(
            band="confirm",
            probability=100.0,
            waitlist_type=quota,
            position=position,
            explanation="This class shows confirmed availability.",
        )
    if status != "WL":
        raise ValueError(f"Unknown availability status: {status}")

    model = WAITLIST_QUOTAS_BY_QUOTA[quota]
    ceiling = model.clearance_ceiling * model.seasonal_modifier
    probability = max(0.0, min(1.0, 1 - (position / ceiling))) * 100

    if probability > CONFIRM_THRESHOLD:
        band = "confirm"
    elif probability < LOW_THRESHOLD:
        band = "low"
    else:
        band = "probable"

    return WaitlistPrediction(
        band=band,
        probability=round(probability, 1),
        waitlist_type=model.waitlist_type,
        position=position,
        explanation=_explain(model, position, probability),
    )


def _explain(model, position: int, probability: float) -> str:
    season_note = (
        "for a normal week"
        if model.seasonal_modifier >= 1.0
        else "with festival-period demand pushing this lower"
    )
    return (
        f"{model.waitlist_type}, position {position}. {model.description} "
        f"That puts your odds around {probability:.0f}% {season_note}."
    )
