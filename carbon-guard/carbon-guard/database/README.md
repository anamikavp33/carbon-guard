# Database module (owner: Antony)

The schema itself is documented in [`../DATABASE_SCHEMA.md`](../DATABASE_SCHEMA.md).
This folder holds the tools to set up, fill, check, back up and clean the MongoDB database.

```
database/
├── README.md                 this file
├── scripts/
│   ├── init_db.py            create indexes, default rules/settings, first admin; list collections
│   └── check_integrity.py    read-only consistency check (credits, trust scores, files)
├── seed/
│   ├── seed_demo_data.py     synthetic demo users + submissions (clearly marked demo data)
│   └── cleanup_demo_data.py  remove demo data (dry run unless --yes)
└── examples/                 example documents with synthetic values (MongoDB Extended JSON)
```

All scripts use the **backend's own code and `.env`**, so they always follow the same rules as the
API. Run them from the `backend` folder with the backend's virtual environment active:

```bat
cd carbon-guard\backend
venv\Scripts\activate
```

## 1. Set up MongoDB Atlas (once)

1. Sign in at https://cloud.mongodb.com and create a free **M0** cluster.
2. **Database Access** → *Add New Database User*: username + generated password (role *Read and write to any database*).
3. **Network Access** → *Add IP Address* → *Add current IP address*. (For a demo on changing networks you can
   add `0.0.0.0/0`, but remove it afterwards.)
4. **Connect** → *Drivers* → Python → copy the `mongodb+srv://...` string.
5. In `backend\.env` set `DB_MODE=atlas` and `MONGO_URI=` the string, with your real password.
   If the password has special characters (`@ : / ? #`), URL-encode them (e.g. `@` → `%40`).
6. Test: `python scripts\check_db.py` must print `SUCCESS`.

Never paste the connection string into chat, documents, screenshots or Git.

## 2. Initialise

```bat
python ..\database\scripts\init_db.py
```
Prints every collection with its document count and indexes. Safe to run many times.

## 3. Demo data (synthetic)

```bat
python ..\database\seed\seed_demo_data.py
```
Creates 3 demo users (`demo.asha@example.com`, `demo.ben@example.com`, `demo.chitra@example.com`,
marked `is_demo: true`) and 8 submissions with computer-drawn pictures, runs them through the real
checks, and makes some admin decisions so every screen has data: verified, rejected, flagged,
pending, credits, Trust Score history, audit logs.

Password: set `DEMO_USER_PASSWORD=...` in `backend\.env` first, or the script prints a random one once.
It refuses to run with `DB_MODE=memory` (the data would vanish immediately).

## 4. Check integrity

```bat
python ..\database\scripts\check_integrity.py
```
Checks the rules in `DATABASE_SCHEMA.md` (credit totals = transactions, Trust Score = latest event,
each verified submission has exactly one award, images exist...). Exit code 1 if anything is wrong.

## 5. Remove test data

```bat
python ..\database\seed\cleanup_demo_data.py           (shows counts only)
python ..\database\seed\cleanup_demo_data.py --yes     (deletes demo users and everything they own)
python ..\database\seed\cleanup_demo_data.py --yes --smoke   (also smoke-test users)
```
Real users are never touched. `geocode_cache` can be emptied any time (it refills itself).

**Retention guidance for the project:** keep only demo data and the team's own test accounts. Before a
public demo, run cleanup, then seed again. Delete uploaded photos of real places/people after the
project review. Do not collect real personal data beyond name and email.

## 6. Backup and restore

Install **MongoDB Database Tools** (https://www.mongodb.com/try/download/database-tools), then in a
Command Prompt (the URI is typed only on your own PC, never shared):

```bat
mongodump --uri "<your MONGO_URI>" --db carbon_guard --out backup\2026-10-25
mongorestore --uri "<your MONGO_URI>" --db carbon_guard --drop backup\2026-10-25\carbon_guard
```
`--drop` replaces the existing collections. Uploaded image files are **not** in MongoDB: also copy
`backend\uploads\`. Atlas M0 has no automatic backups, so take one before each review.

## 7. Example documents

`examples/` contains one document of each main collection, with synthetic values, in MongoDB
Extended JSON (`$oid`, `$date`). They show the exact field names and types. They can be imported for
experiments with `mongoimport --uri "<uri>" --db scratch --collection users --file examples\user.json`
(use a scratch database, not `carbon_guard`).
