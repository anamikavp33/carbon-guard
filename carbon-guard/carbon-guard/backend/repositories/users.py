from pymongo.errors import DuplicateKeyError
from database import get_db
from repositories.helpers import contains, now, to_oid, with_id


def get_by_email(email: str):
    return with_id(get_db().users.find_one({"email": email.lower()}))


def get_by_id(user_id: str):
    return with_id(get_db().users.find_one({"_id": to_oid(user_id, "User")}))


def create(name: str, email: str, password_hash: str, role: str = "user", trust_score: float = 50.0):
    doc = {
        "name": name.strip(),
        "email": email.lower(),
        "password_hash": password_hash,
        "role": role,
        "trust_score": float(trust_score),
        "green_credits_total": 0.0,
        "is_active": True,
        "created_at": now(),
        "updated_at": now(),
    }
    try:
        result = get_db().users.insert_one(doc)
    except DuplicateKeyError:
        return None
    doc["_id"] = result.inserted_id
    return with_id(doc)


def search(text: str = None, skip: int = 0, limit: int = 50):
    query = {"$or": [{"name": contains(text)}, {"email": contains(text)}]} if text else {}
    cur = get_db().users.find(query).sort("created_at", 1).skip(skip).limit(limit)
    return [with_id(d) for d in cur], get_db().users.count_documents(query)


def count(query: dict = None) -> int:
    return get_db().users.count_documents(query or {})


def ensure_admin(email: str, password_hash: str):
    if get_by_email(email) is None:
        create("Carbon Guard Admin", email, password_hash, role="admin")


def set_trust_score(user_id, value: float):
    get_db().users.update_one({"_id": to_oid(user_id)}, {"$set": {"trust_score": value, "updated_at": now()}})


def add_credits(user_id, amount: float):
    get_db().users.update_one({"_id": to_oid(user_id)},
                              {"$inc": {"green_credits_total": amount}, "$set": {"updated_at": now()}})


def set_active(user_id, active: bool):
    get_db().users.update_one({"_id": to_oid(user_id)}, {"$set": {"is_active": active, "updated_at": now()}})
