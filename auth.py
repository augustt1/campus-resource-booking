# auth.py
# ------------------------------------------------------------
# Sign-in and password handling, using Supabase Auth.
#
# Passwords are never stored or checked by our own code: we pass
# the email and password to Supabase over HTTPS and it tells us
# whether they are right. Our database only holds each person's
# university details (the `profiles` table in db/schema.sql).
# ------------------------------------------------------------
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

TIMEOUT = 15

PASSWORD_RULES = [
    "At least 12 characters",
    "No more than 128 characters",
    "An uppercase letter",
    "A lowercase letter",
    "A number",
    "A special character",
]


class AuthUnavailable(Exception):
    """The sign-in service could not be reached or is not configured."""


def _config():
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_ANON_KEY", "")
    if not url or not key:
        raise AuthUnavailable("SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env")
    return url, key


def sign_in(email, password):
    """Check an email and password with Supabase.

    Returns {"user_id": ..., "access_token": ...} when they are correct,
    or None when they are not. The caller shows the same message either
    way a sign-in fails, so nobody can find out which emails have accounts.
    """
    url, key = _config()
    try:
        r = httpx.post(
            f"{url}/auth/v1/token",
            params={"grant_type": "password"},
            headers={"apikey": key},
            json={"email": email, "password": password},
            timeout=TIMEOUT,
        )
    except httpx.HTTPError as e:
        raise AuthUnavailable(str(e)) from e
    if r.status_code == 200:
        data = r.json()
        return {"user_id": data["user"]["id"], "access_token": data["access_token"]}
    if r.status_code in (400, 401, 403, 422):
        return None
    raise AuthUnavailable(f"Sign-in service returned {r.status_code}")


def change_password(access_token, new_password):
    """Set a new password for the signed-in person. Returns True on success."""
    url, key = _config()
    try:
        r = httpx.put(
            f"{url}/auth/v1/user",
            headers={"apikey": key, "Authorization": f"Bearer {access_token}"},
            json={"password": new_password},
            timeout=TIMEOUT,
        )
    except httpx.HTTPError as e:
        raise AuthUnavailable(str(e)) from e
    return r.status_code == 200


def password_problems(password):
    """Return the rules a proposed password does not meet (empty list = fine)."""
    checks = [
        len(password) >= 12,
        len(password) <= 128,
        any(c.isupper() for c in password),
        any(c.islower() for c in password),
        any(c.isdigit() for c in password),
        any(not c.isalnum() for c in password),
    ]
    return [rule for rule, ok in zip(PASSWORD_RULES, checks) if not ok]
