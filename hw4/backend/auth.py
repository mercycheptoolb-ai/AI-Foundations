"""Create-account / log-in / log-out endpoints and session handling.

Sessions: on login or signup the server creates a random token, stores only
its SHA-256 in the sessions table, and gives the raw token to the browser in
an HttpOnly cookie (JavaScript can't read it). Each request looks the hash up
to find the logged-in user.
"""

import hashlib
import os
import re
import secrets
import sqlite3
import threading
import time
import unicodedata
from collections import defaultdict, deque

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator

from db import db
from passwords import DUMMY_HASH, hash_password, needs_rehash, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

SESSION_COOKIE = "cc_session"
SESSION_DAYS = 7
# Set COOKIE_SECURE=1 when served over HTTPS so the cookie is never sent in clear text.
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "0") == "1"

MIN_PASSWORD = 8
MAX_PASSWORD = 128
MAX_NAME = 50
MAX_EMAIL = 254
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# Letters (any language) separated by single spaces, hyphens, apostrophes, or periods,
# e.g. "Mary-Jane", "O'Brien", "José", "St. John". Blocks newlines and other control text.
NAME_RE = re.compile(r"^[^\W\d_]+(?:[ '’.-]{1,2}[^\W\d_]+)*\.?$")

# Brute-force protection: too many failed logins → temporary lockout.
# Counters live in memory, so restarting the server clears them.
MAX_FAILURES = 5
FAILURE_WINDOW_SECONDS = 15 * 60
# Signup is throttled per IP so it can't be spammed (each one costs a slow hash).
MAX_SIGNUPS = 20
SIGNUP_WINDOW_SECONDS = 60 * 60
MAX_CHAT_MESSAGES = 30
CHAT_WINDOW_SECONDS = 10 * 60
_failures: dict[str, deque[float]] = defaultdict(deque)
_failures_lock = threading.Lock()

INVALID_LOGIN = "Incorrect email or password."


def _encodable(value: str) -> str:
    # Reject strings that can't be UTF-8 encoded (e.g. lone surrogates from
    # hand-crafted JSON) with a clean 422 instead of a crash in the hasher.
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError("contains invalid characters")
    return value


class SignupRequest(BaseModel):
    # Generous hard caps; friendlier limits are checked in _validate_signup.
    first_name: str = Field(max_length=200)
    last_name: str = Field(max_length=200)
    email: str = Field(max_length=320)
    password: str = Field(max_length=1024)

    _check_encoding = field_validator("first_name", "last_name", "email", "password")(_encodable)


class LoginRequest(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(max_length=1024)

    _check_encoding = field_validator("email", "password")(_encodable)


# ---------- helpers ----------

def normalize_email(email: str) -> str:
    return email.strip().lower()


def public_user(row: sqlite3.Row) -> dict:
    # Whitelist of fields that may leave the server. Never includes password_hash.
    return {
        "id": row["id"],
        "first_name": row["first_name"] or row["name"].split(" ")[0],
        "last_name": row["last_name"] or "",
        "email": row["email"],
    }


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _start_session(response: Response, user_id: int) -> None:
    token = secrets.token_urlsafe(32)
    with db(write=True) as conn:
        conn.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at) "
            "VALUES (?, ?, datetime('now', ?))",
            (_hash_token(token), user_id, f"+{SESSION_DAYS} days"),
        )
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_DAYS * 24 * 3600,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


def current_user(request: Request) -> dict | None:
    """Return the logged-in user for this request, or None."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    with db() as conn:
        row = conn.execute(
            """
            SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ? AND s.expires_at > datetime('now')
            """,
            (_hash_token(token),),
        ).fetchone()
    return public_user(row) if row else None


def _client_ip(request: Request) -> str:
    # Uvicorn trusts X-Forwarded-For from localhost by default, so a client could
    # fake a new "IP" on every request. Our dev proxy (Vite) never adds that
    # header, so any request carrying it shares one bucket and can't dodge limits.
    if "x-forwarded-for" in request.headers or "forwarded" in request.headers:
        return "forwarded-header"
    return request.client.host if request.client else "unknown"


def throttle(request: Request, kind: str, who: str | None = None) -> None:
    """Count one attempt against a limit in _LIMITS; raise 429 when it's used up."""
    keys = [f"{kind}:{who or _client_ip(request)}"]
    _check_rate_limit(keys)
    _record_failure(keys)


def _rate_limit_keys(request: Request, email: str) -> list[str]:
    return [f"email:{email}", f"ip:{_client_ip(request)}"]


# key prefix -> (max attempts, window in seconds, message)
_LIMITS = {
    "email": (MAX_FAILURES, FAILURE_WINDOW_SECONDS, "Too many failed login attempts. Please try again in about {minutes} min."),
    # Looser per-IP limit so a shared network isn't locked out by one user.
    "ip": (MAX_FAILURES * 4, FAILURE_WINDOW_SECONDS, "Too many failed login attempts. Please try again in about {minutes} min."),
    "signup-ip": (MAX_SIGNUPS, SIGNUP_WINDOW_SECONDS, "Too many sign-up attempts from this network. Please try again in about {minutes} min."),
    # Each chat message is a paid model call.
    "chat": (MAX_CHAT_MESSAGES, CHAT_WINDOW_SECONDS, "You've sent a lot of messages in a short time. Please try again in about {minutes} min."),
}


def _check_rate_limit(keys: list[str]) -> None:
    now = time.monotonic()
    with _failures_lock:
        for key in keys:
            limit, window, message = _LIMITS[key.split(":", 1)[0]]
            # .get (not [key]) so merely checking never creates entries; this
            # keeps memory bounded by real failures, not by every email tried.
            attempts = _failures.get(key)
            if attempts is None:
                continue
            while attempts and now - attempts[0] > window:
                attempts.popleft()
            if not attempts:
                del _failures[key]
                continue
            if len(attempts) >= limit:
                retry = int(window - (now - attempts[0])) + 1
                raise HTTPException(
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    message.format(minutes=max(1, round(retry / 60))),
                    headers={"Retry-After": str(retry)},
                )


def _record_failure(keys: list[str]) -> None:
    now = time.monotonic()
    with _failures_lock:
        for key in keys:
            _failures[key].append(now)


def _clear_failures(email: str) -> None:
    with _failures_lock:
        _failures.pop(f"email:{email}", None)


def _validate_signup(body: SignupRequest) -> tuple[str, str, str]:
    # Collapse runs of whitespace (including newlines) to single spaces.
    first = " ".join(unicodedata.normalize("NFC", body.first_name).split())
    last = " ".join(unicodedata.normalize("NFC", body.last_name).split())
    email = normalize_email(body.email)
    if not first or not last:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Please enter your first and last name.")
    if len(first) > MAX_NAME or len(last) > MAX_NAME:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Names must be {MAX_NAME} characters or fewer.")
    if not NAME_RE.match(first) or not NAME_RE.match(last):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Names can only use letters, spaces, hyphens, apostrophes, and periods.",
        )
    if len(email) > MAX_EMAIL or not EMAIL_RE.match(email):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Please enter a valid email address.")
    if len(body.password) < MIN_PASSWORD:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Password must be at least {MIN_PASSWORD} characters."
        )
    if len(body.password) > MAX_PASSWORD:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Password must be {MAX_PASSWORD} characters or fewer."
        )
    return first, last, email


# ---------- endpoints ----------

@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, request: Request, response: Response) -> dict:
    first, last, email = _validate_signup(body)
    throttle(request, "signup-ip")  # counts every attempt, not just failures

    # Note: telling the user an email is taken is a deliberate UX trade-off;
    # without email verification there is no way to hide it at signup.
    with db() as conn:
        exists = conn.execute("SELECT 1 FROM users WHERE lower(email) = ?", (email,)).fetchone()
    if exists:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "An account with this email already exists. Try logging in instead.",
        )

    password_hash = hash_password(body.password)  # slow; only once we know we'll insert
    try:
        with db(write=True) as conn:
            cur = conn.execute(
                "INSERT INTO users (name, email, password_hash, first_name, last_name) "
                "VALUES (?, ?, ?, ?, ?)",
                (f"{first} {last}", email, password_hash, first, last),
            )
            user_id = cur.lastrowid
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    except sqlite3.IntegrityError:
        # Two signups for the same email raced each other.
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "An account with this email already exists. Try logging in instead.",
        )
    _start_session(response, user_id)
    return {"user": public_user(row)}


@router.post("/login")
def login(body: LoginRequest, request: Request, response: Response) -> dict:
    email = normalize_email(body.email)
    keys = _rate_limit_keys(request, email)
    _check_rate_limit(keys)

    if not email or not body.password or len(body.password) > MAX_PASSWORD:
        _record_failure(keys)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, INVALID_LOGIN)

    with db() as conn:
        row = conn.execute("SELECT * FROM users WHERE lower(email) = ?", (email,)).fetchone()

    if row is None:
        verify_password(body.password, DUMMY_HASH)  # equalize timing
        _record_failure(keys)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, INVALID_LOGIN)

    if not verify_password(body.password, row["password_hash"]):
        _record_failure(keys)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, INVALID_LOGIN)

    _clear_failures(email)
    if needs_rehash(row["password_hash"]):
        # Upgrade older/weaker hashes now that we briefly know the password.
        with db(write=True) as conn:
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (hash_password(body.password), row["id"]),
            )
    _start_session(response, row["id"])
    return {"user": public_user(row)}


@router.post("/logout")
def logout(request: Request, response: Response) -> dict:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        with db(write=True) as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_hash_token(token),))
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="lax", secure=COOKIE_SECURE)
    return {"ok": True}


@router.get("/me")
def me(request: Request) -> dict:
    user = current_user(request)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not logged in.")
    return {"user": user}
