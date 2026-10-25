"""Remove demo data (and optionally smoke-test users) and everything that belongs to them.

    python ..\\database\\seed\\cleanup_demo_data.py            -> shows what WOULD be deleted (nothing deleted)
    python ..\\database\\seed\\cleanup_demo_data.py --yes      -> deletes it
    add --smoke to also remove users created by backend/scripts/smoke_test.py (smoke-xxxx@example.com)

Only users with `is_demo: true` (or smoke-test emails) are touched, together with their submissions,
image files, credit transactions, trust events and fraud logs. Real users are never touched.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend")))


def demo_user_query(include_smoke: bool) -> dict:
    query = [{"is_demo": True}]
    if include_smoke:
        query.append({"email": {"$regex": r"^smoke-[0-9a-f]{8}@example\.com$"}})
    return {"$or": query, "role": "user"}


def cleanup(db, upload_dir: str, include_smoke: bool, really: bool) -> dict:
    users = list(db.users.find(demo_user_query(include_smoke), {"email": 1}))
    ids = [u["_id"] for u in users]
    subs = list(db.submissions.find({"user_id": {"$in": ids}}, {"image_filename": 1}))
    sub_ids = [s["_id"] for s in subs]
    counts = {
        "users": len(users),
        "submissions": len(subs),
        "credit_transactions": db.credit_transactions.count_documents({"user_id": {"$in": ids}}),
        "trust_score_events": db.trust_score_events.count_documents({"user_id": {"$in": ids}}),
        "fraud_logs": db.fraud_logs.count_documents({"submission_id": {"$in": sub_ids}}),
    }
    if really:
        for s in subs:
            for path in (os.path.join(upload_dir, s.get("image_filename") or "-"),
                         os.path.join(upload_dir, "satellite", f"{s['_id']}.png")):
                if os.path.isfile(path):
                    os.remove(path)
        db.credit_transactions.delete_many({"user_id": {"$in": ids}})
        db.trust_score_events.delete_many({"user_id": {"$in": ids}})
        db.fraud_logs.delete_many({"submission_id": {"$in": sub_ids}})
        db.submissions.delete_many({"_id": {"$in": sub_ids}})
        db.users.delete_many({"_id": {"$in": ids}})
    return counts


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--yes", action="store_true", help="really delete (otherwise only show counts)")
    p.add_argument("--smoke", action="store_true", help="also remove smoke-test users")
    args = p.parse_args()

    from config import settings
    import database
    counts = cleanup(database.get_db(), settings.UPLOAD_DIR, args.smoke, args.yes)
    for k, v in counts.items():
        print(f"  {k:<20} {v}")
    print("Deleted." if args.yes else "Nothing deleted. Run again with --yes to delete these.")
    database.close()


if __name__ == "__main__":
    main()
