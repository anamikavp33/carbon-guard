"""Run this to test your MongoDB Atlas connection:   python scripts/check_db.py

It prints plain-language results and the most likely fix for common problems.
"""
import os
import platform
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("Python:", sys.version.split()[0], "on", platform.system())
if sys.version_info >= (3, 14):
    print("WARNING: Python 3.14 is very new. If the connection fails with an SSL/TLS error,")
    print("         install Python 3.12 and recreate the virtual environment.")

from config import settings  # noqa: E402

if settings.DB_MODE != "atlas":
    print("DB_MODE is '%s'. Set DB_MODE=atlas in .env to test Atlas." % settings.DB_MODE)
    sys.exit(1)
if not settings.MONGO_URI:
    print("MONGO_URI is empty. Fill it in .env (see .env.example).")
    sys.exit(1)

try:
    import certifi
    from pymongo import MongoClient

    client = MongoClient(settings.MONGO_URI, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=10000)
    client.admin.command("ping")
    print("SUCCESS: connected to MongoDB Atlas.")
    print("Databases:", client.list_database_names())
except Exception as e:
    text = str(e)
    print("FAILED:", text[:400])
    if "SSL" in text or "TLS" in text:
        print("\nLikely cause: SSL/TLS problem. Try, in this order:")
        print(" 1. Use Python 3.12 (not 3.14) in a fresh virtual environment.")
        print(" 2. In Atlas > Network Access, add your current IP (or 0.0.0.0/0 for testing).")
        print(" 3. Try another network (a mobile hotspot): some college/ISP networks block Atlas.")
        print(" 4. pip install --upgrade pymongo certifi")
    elif "Authentication" in text or "auth" in text.lower():
        print("\nLikely cause: wrong username/password in MONGO_URI (special characters must be URL-encoded).")
    elif "timed out" in text.lower() or "ServerSelection" in text:
        print("\nLikely cause: network access. Add your IP in Atlas > Network Access.")
    sys.exit(1)
