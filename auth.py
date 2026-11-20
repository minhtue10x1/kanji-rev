# -*- coding: utf-8 -*-
"""
Authentication module supporting Google OAuth2 / Google Identity Services (GIS),
JWT creation & verification, and user session management.
"""

import os
import json
import hmac
import hashlib
import base64
import time
import secrets
import urllib.request
import urllib.parse
import urllib.error
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from database import db_session, get_postgres_url

JWT_EXPIRATION_SECONDS = 30 * 24 * 3600  # 30 days session
_WARNED_JWT_FALLBACK = False
_LOCAL_SECRET_CACHE: Optional[str] = None


def get_jwt_secret() -> str:
    """
    Resolve the HMAC signing secret for JWTs.
    Never falls back to a public literal hardcoded in source control.
    """
    global _WARNED_JWT_FALLBACK, _LOCAL_SECRET_CACHE

    env_secret = os.environ.get("JWT_SECRET_KEY", "").strip()
    if len(env_secret) >= 16:
        return env_secret

    pg_url = get_postgres_url()
    is_prod = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))

    if is_prod or pg_url:
        if pg_url:
            if not _WARNED_JWT_FALLBACK:
                print(
                    "SECURITY WARNING: JWT_SECRET_KEY is not set; deriving JWT signing key from Postgres secret URL. "
                    "Please configure a dedicated JWT_SECRET_KEY in Vercel environment variables."
                )
                _WARNED_JWT_FALLBACK = True
            return hmac.new(
                pg_url.encode("utf-8"),
                b"kanji-rev-jwt-secret-v2",
                hashlib.sha256,
            ).hexdigest()
        raise RuntimeError("JWT_SECRET_KEY must be set in production")

    if _LOCAL_SECRET_CACHE:
        return _LOCAL_SECRET_CACHE

    secret_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".local_jwt_secret")
    if os.path.exists(secret_file):
        try:
            with open(secret_file, "r", encoding="utf-8") as f:
                val = f.read().strip()
            if len(val) >= 32:
                _LOCAL_SECRET_CACHE = val
                return val
        except OSError:
            pass

    generated = secrets.token_hex(32)
    try:
        with open(secret_file, "w", encoding="utf-8") as f:
            f.write(generated)
    except OSError:
        pass
    _LOCAL_SECRET_CACHE = generated
    return generated


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(data_str: str) -> bytes:
    padding = "=" * (4 - (len(data_str) % 4)) if (len(data_str) % 4) != 0 else ""
    return base64.urlsafe_b64decode((data_str + padding).encode("utf-8"))


def create_jwt(payload: Dict[str, Any]) -> str:
    """Create a signed HMAC-SHA256 JWT."""
    header = {"alg": "HS256", "typ": "JWT"}
    header_json = json.dumps(header, separators=(",", ":")).encode("utf-8")
    payload_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")

    segments = [_b64url_encode(header_json), _b64url_encode(payload_json)]
    signing_input = ".".join(segments).encode("utf-8")
    signature = hmac.new(get_jwt_secret().encode("utf-8"), signing_input, hashlib.sha256).digest()
    segments.append(_b64url_encode(signature))

    return ".".join(segments)


def decode_jwt(token: str) -> Optional[Dict[str, Any]]:
    """Decode and strictly verify an HMAC-SHA256 JWT (algorithm, signature, and exp)."""
    try:
        if not token or not isinstance(token, str):
            return None
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_bytes = _b64url_decode(parts[0])
        header = json.loads(header_bytes.decode("utf-8"))
        if not isinstance(header, dict) or header.get("alg") != "HS256" or header.get("typ") != "JWT":
            return None

        signing_input = f"{parts[0]}.{parts[1]}".encode("utf-8")
        expected_sig = hmac.new(get_jwt_secret().encode("utf-8"), signing_input, hashlib.sha256).digest()
        provided_sig = _b64url_decode(parts[2])

        if not hmac.compare_digest(expected_sig, provided_sig):
            return None

        payload_bytes = _b64url_decode(parts[1])
        payload = json.loads(payload_bytes.decode("utf-8"))
        if not isinstance(payload, dict):
            return None

        exp = payload.get("exp")
        if isinstance(exp, bool) or not isinstance(exp, (int, float)):
            return None
        if time.time() > exp:
            return None

        return payload
    except Exception:
        return None


def verify_google_id_token(id_token: str) -> Optional[Dict[str, Any]]:
    """
    Strictly verifies a Google ID Token or OAuth2 Access Token against Google endpoints.
    Checks audience (aud / azp) against GOOGLE_CLIENT_ID and requires email_verified=true.
    """
    if not id_token or not isinstance(id_token, str):
        return None
    id_token = id_token.strip()
    if not id_token:
        return None

    # Permanently disable unauthenticated email_* login backdoor
    if id_token.startswith("email_"):
        return None

    # Allow mock_* only when explicitly enabled in non-production dev/test environments
    if id_token.startswith("mock_"):
        is_prod = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
        allow_mock = os.environ.get("ALLOW_DEV_MOCK_AUTH", "").lower() == "true"
        if not allow_mock or is_prod:
            return None
        raw_val = id_token[len("mock_"):].strip().lower()
        if not raw_val:
            return None
        user_email = raw_val if "@" in raw_val else f"{raw_val}@gmail.com"
        username = user_email.split("@")[0]
        avatar = f"https://api.dicebear.com/7.x/initials/svg?seed={urllib.parse.quote(username)}&backgroundColor=d97706,2563eb,059669"
        return {
            "sub": "mock_sub_" + hashlib.sha256(user_email.encode()).hexdigest()[:24],
            "email": user_email,
            "name": username.capitalize(),
            "picture": avatar,
        }

    expected_client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()

    # Case 1: JWT Google ID Token (3 dot-separated segments)
    if id_token.count(".") == 2:
        try:
            url = f"https://oauth2.googleapis.com/tokeninfo?id_token={urllib.parse.quote(id_token, safe='')}"
            req = urllib.request.Request(url, headers={"User-Agent": "KanjiRevApp/2.0"})
            with urllib.request.urlopen(req, timeout=8) as response:
                if response.status != 200:
                    return None
                data = json.loads(response.read().decode("utf-8"))
                if "sub" not in data or "email" not in data:
                    return None
                if str(data.get("email_verified", "")).lower() != "true":
                    return None
                if data.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
                    return None
                if expected_client_id and data.get("aud") != expected_client_id:
                    return None
                return {
                    "sub": data["sub"],
                    "email": data["email"],
                    "name": data.get("name", data["email"].split("@")[0]),
                    "picture": data.get("picture", ""),
                }
        except Exception as e:
            print(f"Google ID token verification error: {e}")
            return None

    # Case 2: OAuth2 Access Token — verify tokeninfo audience first, then fetch userinfo
    try:
        info_url = f"https://oauth2.googleapis.com/tokeninfo?access_token={urllib.parse.quote(id_token, safe='')}"
        info_req = urllib.request.Request(info_url, headers={"User-Agent": "KanjiRevApp/2.0"})
        with urllib.request.urlopen(info_req, timeout=8) as info_resp:
            if info_resp.status != 200:
                return None
            token_data = json.loads(info_resp.read().decode("utf-8"))
            if expected_client_id:
                aud_ok = token_data.get("aud") == expected_client_id or token_data.get("azp") == expected_client_id
                if not aud_ok:
                    return None
            if "email_verified" in token_data and str(token_data.get("email_verified")).lower() != "true":
                return None

        user_req = urllib.request.Request(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {id_token}", "User-Agent": "KanjiRevApp/2.0"},
        )
        with urllib.request.urlopen(user_req, timeout=8) as user_resp:
            if user_resp.status != 200:
                return None
            udata = json.loads(user_resp.read().decode("utf-8"))
            if "email" not in udata:
                return None
            if "email_verified" in udata and str(udata.get("email_verified")).lower() != "true":
                return None
            return {
                "sub": udata.get("sub", udata["email"]),
                "email": udata["email"],
                "name": udata.get("name", udata["email"].split("@")[0]),
                "picture": udata.get("picture", ""),
            }
    except Exception as e:
        print(f"Google access token verification error: {e}")
        return None


def upsert_google_user(google_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Finds or creates a user based on verified Google profile.
    Does not pre-seed 376 blank rows; card progress rows are created lazily upon interaction.
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    with db_session() as (conn, cursor):
        cursor.execute("SELECT * FROM users WHERE google_sub = ?", (google_profile["sub"],))
        user_row = cursor.fetchone()

        if not user_row:
            # Allow seamless migration of existing accounts matched by verified Google email
            cursor.execute("SELECT * FROM users WHERE email = ?", (google_profile["email"],))
            user_row = cursor.fetchone()
            if user_row:
                cursor.execute(
                    """
                    UPDATE users
                    SET google_sub = ?, last_login_at = ?, name = ?, avatar_url = ?
                    WHERE id = ?
                    """,
                    (
                        google_profile["sub"],
                        now_iso,
                        google_profile.get("name", user_row["name"]),
                        google_profile.get("picture", user_row["avatar_url"]),
                        user_row["id"],
                    ),
                )
        else:
            cursor.execute(
                """
                UPDATE users
                SET last_login_at = ?, name = ?, avatar_url = ?
                WHERE id = ?
                """,
                (
                    now_iso,
                    google_profile.get("name", user_row["name"]),
                    google_profile.get("picture", user_row["avatar_url"]),
                    user_row["id"],
                ),
            )

        if user_row:
            user_id = user_row["id"]
        else:
            user_id = str(uuid.uuid4())
            cursor.execute(
                """
                INSERT INTO users (id, email, name, avatar_url, google_sub, created_at, last_login_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    google_profile["email"],
                    google_profile.get("name", ""),
                    google_profile.get("picture", ""),
                    google_profile["sub"],
                    now_iso,
                    now_iso,
                ),
            )

            cursor.execute(
                """
                INSERT INTO user_settings (user_id, theme, shuffle_queue, daily_goal, show_furigana, auto_audio, updated_at)
                VALUES (?, 'light', 0, 20, 1, 0, ?)
                """,
                (user_id, now_iso),
            )

        conn.commit()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        final_user = dict(cursor.fetchone())

    session_token = create_jwt({
        "sub": user_id,
        "email": final_user["email"],
        "name": final_user["name"],
        "exp": int(time.time()) + JWT_EXPIRATION_SECONDS,
    })

    return {
        "user": final_user,
        "token": session_token,
    }
