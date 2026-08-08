"""Multi-user account storage: signup/login + per-user state persistence.

Passwords are never stored in plain text -- only a salted PBKDF2-HMAC-SHA256
hash, compared with a constant-time comparison to avoid timing side-channels.
Each account owns its own profile_store "state" dict (profile, weight
history, disliked meals, weekly recipe history), so different users never
see each other's plans or memory.
"""

import hashlib
import hmac
import json
import os
import re

from storage import profile_store

USERS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "users_data.json")

PBKDF2_ITERATIONS = 200_000
USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,20}$")
MIN_PASSWORD_LENGTH = 8


def _load_all():
    if not os.path.exists(USERS_PATH):
        return {"users": {}}
    with open(USERS_PATH, "r") as f:
        return json.load(f)


def _save_all(data):
    with open(USERS_PATH, "w") as f:
        json.dump(data, f, indent=2)


def _hash_password(password, salt=None):
    if salt is None:
        salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return salt.hex(), digest.hex()


def valid_username(username):
    return bool(USERNAME_RE.match(username or ""))


def username_taken(username):
    data = _load_all()
    return (username or "").lower() in data["users"]


def create_account(username, password, name):
    """Create a new account and return its fresh state dict.

    Raises ValueError with a user-facing message on any validation failure.
    """
    if not name or not name.strip():
        raise ValueError("Please enter your name.")
    if not valid_username(username):
        raise ValueError("Username must be 3-20 characters: letters, numbers, or underscore only.")
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")

    data = _load_all()
    key = username.lower()
    if key in data["users"]:
        raise ValueError("That username is already taken.")

    salt_hex, hash_hex = _hash_password(password)
    state = profile_store.default_state()
    state["profile"]["name"] = name.strip()

    data["users"][key] = {
        "username": username,
        "name": name.strip(),
        "salt": salt_hex,
        "password_hash": hash_hex,
        "state": state,
    }
    _save_all(data)
    return state


def verify_login(username, password):
    """Returns (canonical_username, state) on success, or (None, None) on failure."""
    data = _load_all()
    record = data["users"].get((username or "").lower())
    if record is None:
        return None, None

    salt = bytes.fromhex(record["salt"])
    _, candidate_hash = _hash_password(password or "", salt)
    if not hmac.compare_digest(candidate_hash, record["password_hash"]):
        return None, None

    state = record["state"]
    defaults = profile_store.default_state()
    for key, value in defaults.items():
        state.setdefault(key, value)
    for key, value in defaults["profile"].items():
        state["profile"].setdefault(key, value)
    return record["username"], state


def save_state(username, state):
    data = _load_all()
    key = (username or "").lower()
    if key not in data["users"]:
        raise ValueError(f"Unknown user: {username}")
    data["users"][key]["state"] = state
    _save_all(data)
