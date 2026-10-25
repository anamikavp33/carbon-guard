"""Check that the stored data is consistent (rules in DATABASE_SCHEMA.md, "Data integrity rules").

    python ..\\database\\scripts\\check_integrity.py      (from carbon-guard\\backend, venv active)

Prints every problem found and exits with code 1 if there are any. It only READS the database.
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend")))


def check(db, upload_dir: str) -> list[str]:
    from repositories.config_store import get as get_config
    cfg = get_config()
    problems = []

    users = {u["_id"]: u for u in db.users.find()}
    awards = defaultdict(list)                 # submission_id -> transactions
    credit_sum = defaultdict(float)            # user_id -> total
    for t in db.credit_transactions.find():
        awards[t["submission_id"]].append(t)
        credit_sum[t["user_id"]] += t["amount"]
    last_event = {}
    for e in db.trust_score_events.find().sort("created_at", 1):
        last_event[e["user_id"]] = e

    for uid, u in users.items():
        who = f"user {u['email']}"
        if abs(u.get("green_credits_total", 0) - credit_sum.get(uid, 0)) > 0.01:
            problems.append(f"{who}: green_credits_total {u.get('green_credits_total')} "
                            f"!= sum of transactions {round(credit_sum.get(uid, 0), 2)}")
        expected = last_event[uid]["score_after"] if uid in last_event else None
        if expected is not None and abs(u["trust_score"] - expected) > 0.01:
            problems.append(f"{who}: trust_score {u['trust_score']} != latest event score_after {expected}")
        if not cfg["trust_min"] <= u["trust_score"] <= cfg["trust_max"]:
            problems.append(f"{who}: trust_score {u['trust_score']} outside {cfg['trust_min']}-{cfg['trust_max']}")

    for s in db.submissions.find():
        sid = f"submission {s['_id']}"
        tx = awards.get(s["_id"], [])
        if s["user_id"] not in users:
            problems.append(f"{sid}: user_id {s['user_id']} does not exist")
        if s["status"] == "verified" and len(tx) != 1:
            problems.append(f"{sid}: verified but has {len(tx)} credit award(s) (expected 1)")
        if s["status"] != "verified" and tx:
            problems.append(f"{sid}: status '{s['status']}' but has a credit award")
        if tx and abs(s.get("green_credits_awarded", 0) - tx[0]["amount"]) > 0.01:
            problems.append(f"{sid}: green_credits_awarded {s.get('green_credits_awarded')} != award {tx[0]['amount']}")
        if not os.path.isfile(os.path.join(upload_dir, s.get("image_filename", ""))):
            problems.append(f"{sid}: image file {s.get('image_filename')} is missing from {upload_dir}")
    return problems


def main():
    from config import settings
    import database
    db = database.get_db()
    problems = check(db, settings.UPLOAD_DIR)
    print(f"Checked {db.users.count_documents({})} users and {db.submissions.count_documents({})} submissions.")
    for p in problems:
        print("PROBLEM:", p)
    print("No problems found." if not problems else f"{len(problems)} problem(s) found.")
    database.close()
    raise SystemExit(1 if problems else 0)


if __name__ == "__main__":
    main()
