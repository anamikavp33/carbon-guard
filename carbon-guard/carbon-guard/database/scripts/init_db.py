"""Create all indexes, default credit rules, default settings and the first admin account.

    cd carbon-guard\\backend
    venv\\Scripts\\activate
    python ..\\database\\scripts\\init_db.py

Safe to run many times: nothing is duplicated or overwritten. The backend also does this on every
start, so this script is mainly for checking a fresh Atlas cluster before the first run.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend")))

from config import settings  # noqa: E402
import database  # noqa: E402


def main():
    settings.validate()
    db = database.get_db()
    database.init_db()
    print(f"Database '{settings.DATABASE_NAME}' ({settings.DB_MODE}) is initialised.\n")
    print(f"{'collection':<22}{'documents':>10}   indexes")
    for name in sorted(db.list_collection_names()):
        indexes = ", ".join(sorted(db[name].index_information()))
        print(f"{name:<22}{db[name].count_documents({}):>10}   {indexes}")
    database.close()


if __name__ == "__main__":
    main()
