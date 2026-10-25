"""Shared types used by every API model."""
from datetime import datetime, timezone
from typing import Annotated, Generic, Literal, TypeVar
from pydantic import AfterValidator, BaseModel

ActivityType = Literal["tree_plantation", "solar_panel", "water_harvesting"]
SubmissionStatus = Literal["processing", "pending", "manual_review", "verified", "rejected"]
ACTIVITY_TYPES = ["tree_plantation", "solar_panel", "water_harvesting"]
STATUSES = ["processing", "pending", "manual_review", "verified", "rejected"]


def _as_utc(d: datetime) -> datetime:
    # MongoDB gives back naive datetimes that are really UTC. Marking them as UTC makes the
    # API send e.g. "2026-10-25T06:50:22.925000Z", which every client parses correctly.
    return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d.astimezone(timezone.utc)


UTCDateTime = Annotated[datetime, AfterValidator(_as_utc)]

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """A page of a longer list. Ask for the next page with ?skip=<skip+limit>."""
    items: list[T]
    total: int
    skip: int
    limit: int
