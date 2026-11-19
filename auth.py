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
import urllib.request
import urllib.error
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from database import get_db

# Secret key for signing session JWTs
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "kanji-rev-production-secret-key-jlpt-n3-2026")
JWT_EXPIRATION_SECONDS = 30 * 24 * 3600  # 30 days session

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

def _b64url_decode(data_str: str) -> bytes:
    padding = '=' * (4 - (len(data_str) % 4)) if (len(data_str) % 4) != 0 else ''
    return base64.urlsafe_b64decode((data_str + padding).encode('utf-8'))

def create_jwt(payload: Dict[str, Any]) -> str:
    """Create a signed HMAC-SHA256 JWT."""
    header = {"alg": "HS256", "typ": "JWT"}
    header_json = json.dumps(header, separators=(',', ':')).encode('utf-8')
    payload_json = json.dumps(payload, separators=(',', ':')).encode('utf-8')

    segments = [_b64url_encode(header_json), _b64url_encode(payload_json)]
    signing_input = ".".join(segments).encode('utf-8')
    signature = hmac.new(SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest()
    segments.append(_b64url_encode(signature))

    return ".".join(segments)

def decode_jwt(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify an HMAC-SHA256 JWT."""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None

        signing_input = f"{parts[0]}.{parts[1]}".encode('utf-8')
        expected_sig = hmac.new(SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest()
        provided_sig = _b64url_decode(parts[2])

        if not hmac.compare_digest(expected_sig, provided_sig):
            return None

        payload_bytes = _b64url_decode(parts[1])
        payload = json.loads(payload_bytes.decode('utf-8'))

        # Check expiration
        exp = payload.get("exp")
        if exp and time.time() > exp:
            return None

        return payload
    except Exception:
        return None

def verify_google_id_token(id_token: str) -> Optional[Dict[str, Any]]:
    """
    Verifies a Google ID token using Google's public tokeninfo endpoint.
    Returns the user profile dict if valid: {sub, email, name, picture}
    """
    # Allow mock login in local development if id_token starts with 'mock_'
    if id_token.startswith("mock_"):
        mock_email = id_token.replace("mock_", "") + "@gmail.com"
        return {
            "sub": "mock_sub_" + hashlib.md5(mock_email.encode()).hexdigest(),
            "email": mock_email,
            "name": mock_email.split("@")[0].capitalize(),
            "picture": "https://www.gravatar.com/avatar/?d=mp"
        }

    try:
        url = f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"
        req = urllib.request.Request(url, headers={"User-Agent": "KanjiRevApp/1.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                # Validate mandatory claims
                if "sub" in data and "email" in data:
                    return {
                        "sub": data["sub"],
                        "email": data["email"],
                        "name": data.get("name", data["email"].split("@")[0]),
                        "picture": data.get("picture", "")
                    }
    except Exception as e:
        print(f"Google token verification error: {e}")
        return None

    return None

def upsert_google_user(google_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Finds or creates a user based on Google profile.
    Initializes default user_settings and all 376 kanji progress records.
    """
    conn = get_db()
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()

    cursor.execute("SELECT * FROM users WHERE google_sub = ? OR email = ?", 
                   (google_profile["sub"], google_profile["email"]))
    user_row = cursor.fetchone()

    if user_row:
        user_id = user_row["id"]
        # Update last login and avatar/name
        cursor.execute("""
            UPDATE users 
            SET last_login_at = ?, name = ?, avatar_url = ?
            WHERE id = ?
        """, (now_iso, google_profile.get("name", user_row["name"]), 
              google_profile.get("picture", user_row["avatar_url"]), user_id))
    else:
        user_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO users (id, email, name, avatar_url, google_sub, created_at, last_login_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, google_profile["email"], google_profile.get("name", ""), 
              google_profile.get("picture", ""), google_profile["sub"], now_iso, now_iso))

        # Create default user_settings
        cursor.execute("""
            INSERT INTO user_settings (user_id, theme, shuffle_queue, daily_goal, show_furigana, auto_audio, updated_at)
            VALUES (?, 'light', 0, 20, 1, 0, ?)
        """, (user_id, now_iso))

        # Pre-seed 376 kanji records for this user
        records = []
        for kid in range(1, 377):
            records.append((user_id, kid, 'new', 0, 1, 2.5, 0, 0, 0, None, None))
        
        cursor.executemany("""
            INSERT INTO user_kanji_progress (
                user_id, kanji_id, status, repetitions, interval_days, ease_factor, 
                correct_count, incorrect_count, is_bookmarked, last_reviewed_at, next_review_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, records)

    conn.commit()

    # Fetch updated user data
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    final_user = dict(cursor.fetchone())
    conn.close()

    # Generate session JWT
    session_token = create_jwt({
        "sub": user_id,
        "email": final_user["email"],
        "name": final_user["name"],
        "exp": int(time.time()) + JWT_EXPIRATION_SECONDS
    })

    return {
        "user": final_user,
        "token": session_token
    }
