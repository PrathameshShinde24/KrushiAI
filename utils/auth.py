"""
KrushiAI — Authentication Layer (hardened)
Security features:
  - PBKDF2-HMAC-SHA256 password hashing (260k iterations)
  - Rate limiting: 5 failed attempts → 15-minute lockout (stored in MongoDB)
  - Strong password policy: 8+ chars, uppercase, digit, special char
  - Email regex validation
  - No legacy plaintext support (removed)
  - All user strings HTML-escaped before use in templates
"""

import re
from html import escape
import streamlit as st

from utils.database import (
    find_user_by_email, find_user_by_id, create_user,
    update_user_password, update_user_name,
    hash_password, verify_password,
    record_failed_login, is_rate_limited,
    clear_login_attempts, get_remaining_lockout,
)

_EMAIL_RE    = re.compile(r"^[\w.+\-]+@[\w\-]+\.[a-zA-Z]{2,}$")
_UPPER_RE    = re.compile(r"[A-Z]")
_DIGIT_RE    = re.compile(r"[0-9]")
_SPECIAL_RE  = re.compile(r"[!@#$%^&*(),.?\":{}|<>\-_]")
MIN_PWD_LEN  = 8


# ── User model ─────────────────────────────────────────────────────────────────

class LocalUser:
    def __init__(self, id: str, name: str, email: str, created_at):
        self.id         = str(id)
        self.name       = escape(name or "")          # XSS-safe
        self.email      = escape(email or "")         # XSS-safe
        self.created_at = created_at

    def display_name(self) -> str:
        n = self.name.strip()
        return n if n else self.email.split("@")[0].title()


class AuthResponse:
    def __init__(self, user: LocalUser):
        self.user = user


# ── Validation helpers ─────────────────────────────────────────────────────────

def _valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email.strip()))

def _check_password_strength(password: str) -> str | None:
    """Returns an error string, or None if password is strong enough."""
    if len(password) < MIN_PWD_LEN:
        return f"Password must be at least {MIN_PWD_LEN} characters."
    if not _UPPER_RE.search(password):
        return "Password must contain at least one uppercase letter."
    if not _DIGIT_RE.search(password):
        return "Password must contain at least one number."
    if not _SPECIAL_RE.search(password):
        return "Password must contain at least one special character (!@#$%^&* etc.)."
    return None


# ── Public API ─────────────────────────────────────────────────────────────────

def sign_in(email: str, password: str):
    """
    Authenticate user with rate limiting.
    - Locks account for 15 min after 5 failed attempts.
    - Rejects any account with no salt (no legacy plaintext support).
    """
    email = email.strip().lower()

    # ── Rate limit check ──────────────────────────────────────────────────────
    if is_rate_limited(email):
        remaining = get_remaining_lockout(email)
        mins = remaining // 60
        secs = remaining % 60
        st.error(f"Too many failed attempts. Try again in {mins}m {secs}s.")
        return None

    # ── Lookup user ───────────────────────────────────────────────────────────
    doc = find_user_by_email(email)
    if not doc:
        record_failed_login(email)
        st.error("Invalid email or password.")
        return None

    # ── Reject legacy plaintext accounts ─────────────────────────────────────
    salt = doc.get("salt")
    if not salt:
        st.error("Your account uses an outdated format. Please contact support to reset your password.")
        return None

    # ── Verify password ───────────────────────────────────────────────────────
    if not verify_password(password, doc["password"], salt):
        record_failed_login(email)
        remaining_attempts = 5 - (doc.get("attempts", 0) + 1)
        if remaining_attempts > 0:
            st.error(f"Invalid email or password. {remaining_attempts} attempt(s) remaining.")
        else:
            st.error("Too many failed attempts. Account locked for 15 minutes.")
        return None

    # ── Success — clear rate limit counter ────────────────────────────────────
    clear_login_attempts(email)
    name = (doc.get("name") or "").strip() or email.split("@")[0].title()
    return AuthResponse(LocalUser(doc["_id"], name, email, doc.get("created_at")))


def sign_up(email: str, password: str, name: str) -> bool:
    """Register a new user with strong password policy."""
    email = email.strip().lower()
    name  = name.strip()

    if not _valid_email(email):
        st.error("Please enter a valid email address.")
        return False

    if len(name) < 2:
        st.error("Please enter your full name (at least 2 characters).")
        return False

    pwd_error = _check_password_strength(password)
    if pwd_error:
        st.error(pwd_error)
        return False

    hashed, salt = hash_password(password)
    ok = create_user(name, email, hashed, salt)
    if not ok:
        st.error("This email is already registered. Please sign in instead.")
    return ok


def change_password(user_id: str, old_password: str, new_password: str) -> bool:
    """Change password — verifies old password first."""
    doc = find_user_by_id(user_id)
    if not doc:
        return False

    salt = doc.get("salt")
    if not salt or not verify_password(old_password, doc["password"], salt):
        return False

    pwd_error = _check_password_strength(new_password)
    if pwd_error:
        st.error(pwd_error)
        return False

    new_hash, new_salt = hash_password(new_password)
    update_user_password(user_id, new_hash, new_salt)
    return True


def update_profile_name(user_id: str, new_name: str) -> bool:
    """Update display name with basic validation."""
    new_name = new_name.strip()
    if len(new_name) < 2:
        st.error("Name must be at least 2 characters.")
        return False
    update_user_name(user_id, new_name)
    return True
