"""
Atlas Travel Planner — Authentication
File-based user store (JSON).  No extra database required.
Uses werkzeug.security (bundled with Flask) for password hashing.
"""

import os
import json
import re
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session

# ── Storage ───────────────────────────────────────────────────────────────────
USERS_FILE = os.path.join(os.path.dirname(__file__), "data", "users.json")


def _load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def _save_users(users: dict) -> None:
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)


# ── Validation ────────────────────────────────────────────────────────────────
def _valid_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))


def _valid_password(pw: str) -> str | None:
    """Return an error string, or None if valid."""
    if len(pw) < 8:
        return "Password must be at least 8 characters."
    if not re.search(r"[A-Za-z]", pw):
        return "Password must contain at least one letter."
    if not re.search(r"[0-9]", pw):
        return "Password must contain at least one number."
    return None


# ── Public API ────────────────────────────────────────────────────────────────
def register_user(name: str, email: str, password: str) -> tuple[bool, str]:
    """
    Create a new account.
    Returns (True, "") on success or (False, error_message) on failure.
    """
    name     = name.strip()
    email    = email.strip().lower()
    password = password.strip()

    if not name:
        return False, "Full name is required."
    if not _valid_email(email):
        return False, "Please enter a valid email address."
    pw_err = _valid_password(password)
    if pw_err:
        return False, pw_err

    users = _load_users()
    if email in users:
        return False, "An account with this email already exists."

    users[email] = {
        "name":       name,
        "email":      email,
        "password":   generate_password_hash(password),
        "created_at": datetime.utcnow().isoformat(),
        "avatar":     name[0].upper(),
    }
    _save_users(users)
    return True, ""


def login_user(email: str, password: str) -> tuple[bool, str]:
    """
    Verify credentials and populate session.
    Returns (True, "") on success or (False, error_message) on failure.
    """
    email    = email.strip().lower()
    password = password.strip()

    users = _load_users()
    user  = users.get(email)
    if not user or not check_password_hash(user["password"], password):
        return False, "Invalid email or password."

    session["user"] = {
        "name":   user["name"],
        "email":  user["email"],
        "avatar": user["avatar"],
    }
    session.permanent = True
    return True, ""


def logout_user() -> None:
    session.pop("user", None)
    session.pop("conversation", None)


def current_user() -> dict | None:
    """Return the logged-in user dict or None."""
    return session.get("user")


def login_required(f):
    """Route decorator — redirects to /login if not authenticated."""
    from functools import wraps
    from flask import redirect, url_for, request as freq
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user():
            return redirect(url_for("login_page", next=freq.path))
        return f(*args, **kwargs)
    return decorated
