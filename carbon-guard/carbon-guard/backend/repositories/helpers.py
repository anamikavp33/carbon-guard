import re
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)  # stored as naive UTC


def to_oid(value: str, what: str = "id") -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail=f"{what} not found")


def with_id(doc):
    """Return a copy of a Mongo document with `_id` exposed as string `id`."""
    if doc is None:
        return None
    out = dict(doc)
    out["id"] = str(out.pop("_id"))
    for key in ("user_id", "submission_id"):
        if key in out and isinstance(out[key], ObjectId):
            out[key] = str(out[key])
    return out


def contains(text: str) -> dict:
    """Case-insensitive 'contains' filter. User input is escaped so it is never a regex."""
    return {"$regex": re.escape(text), "$options": "i"}
