"""
KrushiAI — MongoDB Database Layer
- Cloud-hosted MongoDB Atlas via pymongo
- Singleton MongoClient cached by Streamlit
- PBKDF2 password hashing (stdlib, no extra deps)
- Aggregation pipeline for fast stats
"""

import os
import hashlib
import streamlit as st
from datetime import datetime, timezone
from pymongo import MongoClient, DESCENDING
from pymongo.errors import DuplicateKeyError
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGODB_URI")
MONGO_DB  = os.getenv("MONGODB_DB", "krushiai")


# ── Connection (cached singleton) ──────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def _client() -> MongoClient:
    return MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

def _db():
    return _client()[MONGO_DB]


# ── Password utilities ─────────────────────────────────────────────────────────

def hash_password(password: str, salt: str = None):
    """Returns (hashed_hex, salt_hex) using PBKDF2-HMAC-SHA256."""
    if salt is None:
        salt = os.urandom(16).hex()
    hashed = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 260_000
    ).hex()
    return hashed, salt

def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    hashed, _ = hash_password(password, salt)
    return hashed == stored_hash


# ── Schema / Indexes ───────────────────────────────────────────────────────────

def init_db():
    """Create indexes. Safe to call on every startup (idempotent)."""
    try:
        db = _db()
        db.users.create_index("email", unique=True)
        db.scans.create_index("user_id")
        db.scans.create_index([("created_at", DESCENDING)])
        db.login_attempts.create_index("email", unique=True)
        # Auto-expire lockout documents after 15 minutes
        db.login_attempts.create_index(
            "last_attempt", expireAfterSeconds=900
        )
    except Exception as e:
        st.warning(f"DB init warning: {e}")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _fmt_date(dt) -> str:
    """Format a datetime or string for display."""
    if isinstance(dt, datetime):
        return dt.strftime("%b %d, %Y  %H:%M")
    return str(dt)[5:16]


# ── Scan operations ────────────────────────────────────────────────────────────

def save_scan_result(user_id: str, disease_name: str,
                     confidence: float, image_name: str = None):
    """Insert a new scan record."""
    _db().scans.insert_one({
        "user_id":      ObjectId(user_id),
        "disease_type": disease_name,
        "confidence":   round(float(confidence), 2),
        "image_name":   image_name,
        "created_at":   datetime.now(timezone.utc),
    })
    st.toast(f"Scan saved: {disease_name}", icon="✅")


# ── Rate limiting ──────────────────────────────────────────────────────────────

MAX_ATTEMPTS  = 5          # max failed logins
LOCKOUT_SECS  = 15 * 60   # 15-minute lockout window

def record_failed_login(email: str):
    """Increment failed login counter for this email."""
    _db().login_attempts.update_one(
        {"email": email.lower()},
        {
            "$inc": {"attempts": 1},
            "$set": {"last_attempt": datetime.now(timezone.utc)},
            "$setOnInsert": {"email": email.lower()},
        },
        upsert=True,
    )

def is_rate_limited(email: str) -> bool:
    """Return True if this email is locked out due to too many failures."""
    from datetime import timedelta
    doc = _db().login_attempts.find_one({"email": email.lower()})
    if not doc:
        return False
    attempts    = doc.get("attempts", 0)
    last_attempt = doc.get("last_attempt")
    if attempts < MAX_ATTEMPTS:
        return False
    # Check if still within lockout window
    if last_attempt:
        elapsed = (datetime.now(timezone.utc) - last_attempt).total_seconds()
        if elapsed < LOCKOUT_SECS:
            return True
        # Window expired — reset counter
        clear_login_attempts(email)
    return False

def clear_login_attempts(email: str):
    """Reset failed login counter after successful login or lockout expiry."""
    _db().login_attempts.delete_one({"email": email.lower()})

def get_remaining_lockout(email: str) -> int:
    """Return seconds remaining in lockout, or 0 if not locked."""
    from datetime import timedelta
    doc = _db().login_attempts.find_one({"email": email.lower()})
    if not doc or doc.get("attempts", 0) < MAX_ATTEMPTS:
        return 0
    last_attempt = doc.get("last_attempt")
    if not last_attempt:
        return 0
    elapsed = (datetime.now(timezone.utc) - last_attempt).total_seconds()
    remaining = int(LOCKOUT_SECS - elapsed)
    return max(remaining, 0)


def delete_scan(scan_id: str, user_id: str):
    """Delete a scan, scoped to the owner."""
    _db().scans.delete_one({
        "_id":     ObjectId(scan_id),
        "user_id": ObjectId(user_id),
    })


def fetch_scan_history(user_id: str) -> list[dict]:
    """All scans for a user, newest first."""
    cursor = _db().scans.find(
        {"user_id": ObjectId(user_id)}
    ).sort("created_at", DESCENDING)

    results = []
    for doc in cursor:
        results.append({
            "id":           str(doc["_id"]),
            "user_id":      str(doc["user_id"]),
            "disease_type": doc.get("disease_type", ""),
            "confidence":   doc.get("confidence", 0.0),
            "image_name":   doc.get("image_name"),
            "created_at":   _fmt_date(doc.get("created_at", "")),
        })
    return results


def get_user_stats(user_id: str) -> dict:
    """Aggregated stats via MongoDB aggregation pipeline."""
    pipeline = [
        {"$match": {"user_id": ObjectId(user_id)}},
        {"$group": {
            "_id": None,
            "total":          {"$sum": 1},
            "healthy":        {"$sum": {"$cond": [{"$eq": ["$disease_type", "Healthy"]}, 1, 0]}},
            "diseased":       {"$sum": {"$cond": [{"$ne": ["$disease_type", "Healthy"]}, 1, 0]}},
            "avg_confidence": {"$avg": "$confidence"},
            "last_scan":      {"$max": "$created_at"},
        }},
    ]
    rows = list(_db().scans.aggregate(pipeline))
    if not rows:
        return {"total": 0, "healthy": 0, "diseased": 0,
                "avg_confidence": 0, "last_scan": None}
    r = rows[0]
    return {
        "total":          r["total"],
        "healthy":        r["healthy"],
        "diseased":       r["diseased"],
        "avg_confidence": round(r["avg_confidence"] or 0, 1),
        "last_scan":      _fmt_date(r["last_scan"]) if r.get("last_scan") else None,
    }


# ── User operations (used by auth.py) ─────────────────────────────────────────

def find_user_by_email(email: str):
    return _db().users.find_one({"email": email.lower()})

def find_user_by_id(user_id: str):
    return _db().users.find_one({"_id": ObjectId(user_id)})

def create_user(name: str, email: str, hashed_pwd: str, salt: str) -> bool:
    """Insert a new user. Returns False on duplicate email."""
    try:
        _db().users.insert_one({
            "name":       name.strip(),
            "email":      email.lower(),
            "password":   hashed_pwd,
            "salt":       salt,
            "created_at": datetime.now(timezone.utc),
        })
        return True
    except DuplicateKeyError:
        return False

def update_user_password(user_id: str, hashed_pwd: str, salt: str):
    _db().users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"password": hashed_pwd, "salt": salt}},
    )

def update_user_name(user_id: str, name: str):
    _db().users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"name": name.strip()}},
    )
