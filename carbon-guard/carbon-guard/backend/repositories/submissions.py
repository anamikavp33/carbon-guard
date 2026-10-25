import math
from database import get_db
from repositories.helpers import contains, to_oid, with_id


def insert(doc: dict) -> dict:
    get_db().submissions.insert_one(doc)
    return with_id(doc)


def get(submission_id: str):
    return with_id(get_db().submissions.find_one({"_id": to_oid(submission_id, "Submission")}))


def update(submission_id: str, changes: dict):
    get_db().submissions.update_one({"_id": to_oid(submission_id)}, {"$set": changes})


def set_status_if(submission_id: str, allowed: list, changes: dict) -> bool:
    """Change a submission only if its status is still one of `allowed`.

    The status check and the update happen in one database operation, so two admins
    clicking at the same time cannot both succeed."""
    res = get_db().submissions.update_one(
        {"_id": to_oid(submission_id), "status": {"$in": allowed}}, {"$set": changes})
    return res.modified_count == 1


def list_for_user(user_id, skip: int = 0, limit: int = 100):
    query = {"user_id": to_oid(str(user_id))}
    cur = get_db().submissions.find(query).sort("created_at", -1).skip(skip).limit(limit)
    return [with_id(d) for d in cur], get_db().submissions.count_documents(query)


def search(status=None, activity_type=None, text=None, skip: int = 0, limit: int = 50):
    query = {}
    if status:
        query["status"] = status
    if activity_type:
        query["activity_type"] = activity_type
    if text:
        query["user_email"] = contains(text)
    cur = get_db().submissions.find(query).sort("created_at", -1).skip(skip).limit(limit)
    return [with_id(d) for d in cur], get_db().submissions.count_documents(query)


def all_matching(query: dict = None, projection: dict = None):
    return [with_id(d) for d in get_db().submissions.find(query or {}, projection)]


def count(query: dict = None) -> int:
    return get_db().submissions.count_documents(query or {})


def find_by_hash(image_hash: str):
    return [with_id(d) for d in get_db().submissions.find({"image_hash": image_hash})]


def all_dhashes():
    """(id, dhash) of every stored image, for similarity comparison.

    Prototype limitation: this reads every hash. Fine for thousands of submissions;
    a large deployment would need an index designed for similarity search."""
    return [
        (str(d["_id"]), d["image_dhash"])
        for d in get_db().submissions.find({}, {"image_dhash": 1})
        if d.get("image_dhash")
    ]


def nearby(lat: float, lng: float, radius_m: float, exclude_id=None):
    """Submissions within radius_m metres. A cheap box query first, then exact distance."""
    dlat = radius_m / 111320.0 * 1.5
    dlng = dlat / max(math.cos(math.radians(lat)), 0.01)
    box = {
        "gps.lat": {"$gte": lat - dlat, "$lte": lat + dlat},
        "gps.lng": {"$gte": lng - dlng, "$lte": lng + dlng},
    }
    found = []
    for d in get_db().submissions.find(box):
        if exclude_id is not None and str(d["_id"]) == str(exclude_id):
            continue
        if haversine_m(lat, lng, d["gps"]["lat"], d["gps"]["lng"]) <= radius_m:
            found.append(with_id(d))
    return found


def count_recent_by_user(user_id, since, exclude_id=None):
    query = {"user_id": to_oid(str(user_id)), "created_at": {"$gte": since}}
    if exclude_id is not None:
        query["_id"] = {"$ne": to_oid(str(exclude_id))}
    return get_db().submissions.count_documents(query)


def haversine_m(lat1, lng1, lat2, lng2) -> float:
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))
