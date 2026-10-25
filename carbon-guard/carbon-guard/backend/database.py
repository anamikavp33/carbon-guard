"""MongoDB connection, collection access, indexes and default data.

DB_MODE=atlas  : real MongoDB Atlas through PyMongo (persistent).
DB_MODE=memory : mongomock, a temporary in-memory stand-in used for development and tests.
                 It is not persistent and must not be used for the final demo data.

The collections and their fields are documented in DATABASE_SCHEMA.md (repository root).
"""
import logging
from config import settings

log = logging.getLogger("carbon_guard")
_client = None
_db = None


def connect():
    global _client, _db
    if settings.DB_MODE == "memory":
        import mongomock  # only needed in memory mode (requirements-dev.txt)
        _client = mongomock.MongoClient()
        log.warning("DB_MODE=memory: using a TEMPORARY in-memory database. Data will be lost on restart.")
    else:
        import certifi
        from pymongo import MongoClient
        _client = MongoClient(
            settings.MONGO_URI,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=10000,
        )
        _client.admin.command("ping")  # fail early with a clear error
    _db = _client[settings.DATABASE_NAME]
    return _db


def get_db():
    if _db is None:
        connect()
    return _db


def close():
    global _client, _db
    if _client is not None:
        _client.close()
    _client, _db = None, None


def create_indexes(db):
    db.users.create_index("email", unique=True)
    db.submissions.create_index([("user_id", 1), ("created_at", -1)])
    db.submissions.create_index([("status", 1), ("created_at", -1)])
    db.submissions.create_index("image_hash")
    db.submissions.create_index([("gps.lat", 1), ("gps.lng", 1)])
    db.green_credit_rules.create_index("activity_type", unique=True)
    # Unique keys make credit awards and trust updates idempotent (cannot be applied twice).
    db.credit_transactions.create_index([("submission_id", 1), ("type", 1)], unique=True)
    db.credit_transactions.create_index([("user_id", 1), ("created_at", -1)])
    db.trust_score_events.create_index("event_key", unique=True)
    db.trust_score_events.create_index([("user_id", 1), ("created_at", 1)])
    db.fraud_logs.create_index("submission_id")
    db.audit_logs.create_index([("created_at", -1)])
    db.geocode_cache.create_index("key", unique=True)
    db.settings.create_index("key", unique=True)


def init_db():
    """Create indexes and default documents. Safe to run many times."""
    from repositories import config_store, credit_rules, users
    from services.auth_service import hash_password

    db = get_db()
    create_indexes(db)
    config_store.ensure_defaults()
    credit_rules.ensure_defaults()
    users.ensure_admin(settings.ADMIN_EMAIL, hash_password(settings.ADMIN_PASSWORD))
