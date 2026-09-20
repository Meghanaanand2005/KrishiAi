"""
auth.py

Simple username/password authentication for KrishiAI, backed by the
`users` table in database.py.

Passwords are never stored in plain text. Each password is hashed with
PBKDF2-HMAC-SHA256 (100,000 iterations) and a random 16-byte salt per
user, using only Python's standard library (hashlib + os) -- no extra
dependency required.
"""

import binascii
import hashlib
import hmac
import os

import database

PBKDF2_ITERATIONS = 100_000


def _hash_password(password: str, salt: bytes) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return binascii.hexlify(dk).decode("utf-8")


def signup(username: str, password: str, name: str, role: str, phone: str = "", location: str = ""):
    """
    Create a new user account.
    Returns (success: bool, message: str).
    """
    username = (username or "").strip().lower()
    name = (name or "").strip()

    if not username or not password or not name:
        return False, "Username, password, and name are all required."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    if role not in ("farmer", "owner"):
        return False, "Invalid role."
    if database.get_user_by_username(username):
        return False, "That username is already taken."

    salt = os.urandom(16)
    password_hash = _hash_password(password, salt)

    database.create_user(
        username=username,
        password_hash=password_hash,
        salt=binascii.hexlify(salt).decode("utf-8"),
        name=name,
        role=role,
        phone=(phone or "").strip(),
        location=(location or "").strip(),
    )
    return True, "Account created! Please log in."


def login(username: str, password: str):
    """
    Verify credentials.
    Returns (user: dict | None, message: str).
    """
    username = (username or "").strip().lower()
    if not username or not password:
        return None, "Please enter a username and password."

    # One message for both failures, so the form can't be used to discover
    # which usernames exist.
    invalid = "Incorrect username or password."

    user = database.get_user_by_username(username)
    if not user:
        return None, invalid

    salt = binascii.unhexlify(user["salt"])
    expected = _hash_password(password, salt)
    if not hmac.compare_digest(expected, user["password_hash"]):
        return None, invalid

    return user, f"Welcome back, {user['name']}!"
