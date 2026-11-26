# -*- coding: utf-8 -*-
"""
High-Performance FastAPI Server for Kanji Master Multi-Level (N5 - N1).
Provides verified Google OAuth2 authentication, multi-level SRS sync, and static web serving.
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Depends, Header, status, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import (
    init_database,
    db_session,
    is_pg_conn,
    DatabaseUnavailableError,
)
from auth import verify_google_id_token, upsert_google_user, decode_jwt

VALID_LEVELS = {"N5", "N4", "N3", "N2", "N1"}
VALID_CARD_STATUSES = {"new", "learning", "mastered"}
VN_TZ = timezone(timedelta(hours=7))


def normalize_level(level: Optional[str]) -> str:
    lvl = (level or "N3").strip().upper()
    if lvl not in VALID_LEVELS:
        raise HTTPException(status_code=400, detail=f"Cấp độ JLPT không hợp lệ: {lvl}")
    return lvl


# Initialize database schema on startup safely
try:
    init_database()
except Exception as e:
    print(f"Warning: Deferred database initialization on startup: {e}")

app = FastAPI(title="Kanji Master Full Multi-Level API", version="2.1.0")

# Strict CORS whitelist
allowed_origins = [
    "https://kanji-rev.vercel.app",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
extra_origins = os.environ.get("ALLOWED_ORIGINS", "")
for origin in extra_origins.split(","):
    clean_origin = origin.strip().rstrip("/")
    if clean_origin and clean_origin not in allowed_origins:
        allowed_origins.append(clean_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(DatabaseUnavailableError)
async def db_unavailable_handler(request: Request, exc: DatabaseUnavailableError):
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Cơ sở dữ liệu tạm thời không khả dụng, vui lòng thử lại sau."},
    )


@app.middleware("http")
async def vercel_path_rewrite_middleware(request: Request, call_next):
    """Normalize paths rewritten by Vercel serverless environment."""
    subpath = request.query_params.get("__path__")
    if subpath:
        clean_subpath = subpath.lstrip("/")
        request.scope["path"] = f"/api/{clean_subpath}"
    elif request.scope.get("path") in ("/api/index.py", "/api/index.py/"):
        request.scope["path"] = "/api"
    return await call_next(request)


@app.get("/api")
def api_health():
    return {
        "status": "ok",
        "message": "Kanji Master API operational",
    }


# -------------------------------------------------------------
# Dependency: Extract Current Authenticated User
# -------------------------------------------------------------
def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Chưa đăng nhập (Thiếu Bearer Token)")

    token = authorization[len("Bearer "):].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Chưa đăng nhập (Thiếu Token)")

    payload = decode_jwt(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Phiên đăng nhập hết hạn hoặc không hợp lệ")

    return payload["sub"]


# -------------------------------------------------------------
# Pydantic Request Models
# -------------------------------------------------------------
class GoogleAuthRequest(BaseModel):
    id_token: str
    level: Optional[str] = "N3"


class SettingsUpdateRequest(BaseModel):
    current_level: Optional[str] = None
    theme: Optional[str] = None
    shuffle_queue: Optional[bool] = None
    daily_goal: Optional[int] = None
    show_furigana: Optional[bool] = None
    auto_audio: Optional[bool] = None


class CardReviewRequest(BaseModel):
    level: Optional[str] = "N3"
    kanji_id: int
    is_correct: bool
    mode: Optional[str] = "flashcard"


class BookmarkToggleRequest(BaseModel):
    level: Optional[str] = "N3"
    kanji_id: int


class SessionSaveRequest(BaseModel):
    level: Optional[str] = "N3"
    mode: str
    filter_type: str
    chapter_num: Optional[int] = None
    queue: List[Any]
    current_index: int
    completed_count: int


class ImportLocalRequest(BaseModel):
    level: Optional[str] = "N3"
    cards: Dict[str, Any]
    bookmarks: Optional[List[int]] = None
    session: Optional[Dict[str, Any]] = None


class ResetProgressRequest(BaseModel):
    level: Optional[str] = "N3"


# -------------------------------------------------------------
# Helpers: Streak & Analytics Computation
# -------------------------------------------------------------
def compute_user_stats(cursor, user_id: str) -> Dict[str, int]:
    """Computes real study streak and review counts from study_logs in VN local timezone."""
    cursor.execute("SELECT COUNT(*) AS cnt FROM study_logs WHERE user_id = ?", (user_id,))
    cnt_row = cursor.fetchone()
    total_reviews = int(cnt_row["cnt"] or 0) if cnt_row else 0

    cursor.execute(
        "SELECT created_at FROM study_logs WHERE user_id = ? ORDER BY created_at DESC LIMIT 5000",
        (user_id,),
    )
    rows = cursor.fetchall()

    today = datetime.now(VN_TZ).date()
    today_reviews = 0
    date_set = set()

    for r in rows:
        raw_ts = r["created_at"]
        if not raw_ts:
            continue
        try:
            dt = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            local_d = dt.astimezone(VN_TZ).date()
            date_set.add(local_d)
            if local_d == today:
                today_reviews += 1
        except ValueError:
            continue

    if not date_set:
        return {
            "currentStreak": 0,
            "bestStreak": 0,
            "todayReviews": 0,
            "totalReviews": total_reviews,
        }

    sorted_desc = sorted(date_set, reverse=True)
    yesterday = today - timedelta(days=1)

    current_streak = 0
    if sorted_desc[0] in (today, yesterday):
        current_streak = 1
        prev = sorted_desc[0]
        for d in sorted_desc[1:]:
            if (prev - d).days == 1:
                current_streak += 1
                prev = d
            else:
                break

    sorted_asc = sorted(date_set)
    best_streak = 1
    run = 1
    for i in range(1, len(sorted_asc)):
        if (sorted_asc[i] - sorted_asc[i - 1]).days == 1:
            run += 1
            if run > best_streak:
                best_streak = run
        else:
            run = 1

    return {
        "currentStreak": current_streak,
        "bestStreak": best_streak,
        "todayReviews": today_reviews,
        "totalReviews": total_reviews,
    }


# -------------------------------------------------------------
# 1. Authentication & Public Config Endpoints
# -------------------------------------------------------------
@app.get("/api/config")
@app.get("/config")
def get_public_config():
    """Public environment configuration for frontend clients."""
    return {
        "google_client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
        "environment": "production" if os.environ.get("VERCEL") else "development",
    }


@app.get("/api/health")
@app.get("/health")
def get_health():
    """Minimal diagnostics endpoint without leaking sensitive infrastructure metadata."""
    try:
        with db_session() as (conn, cursor):
            cursor.execute("SELECT 1")
            cursor.fetchone()
            engine = "postgresql" if is_pg_conn(conn) else "sqlite"
        return {"status": "ok", "engine": engine}
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "error", "detail": "Database unavailable"},
        )


def fetch_user_bundle(user_id: str, level: str = "N3") -> Dict[str, Any]:
    """Helper to fetch full user state (profile, settings, progress, active session, stats) in one pooled connection."""
    lvl = normalize_level(level)

    with db_session() as (conn, cursor):
        cursor.execute(
            "SELECT id, email, name, avatar_url, created_at, last_login_at FROM users WHERE id = ?",
            (user_id,),
        )
        user_row = cursor.fetchone()
        if not user_row:
            return {}

        cursor.execute("SELECT * FROM user_settings WHERE user_id = ?", (user_id,))
        settings_row = cursor.fetchone()

        cursor.execute(
            """
            SELECT kanji_id, status, repetitions, interval_days, ease_factor,
                   correct_count, incorrect_count, is_bookmarked, last_reviewed_at, next_review_at
            FROM user_kanji_progress
            WHERE user_id = ? AND level = ?
            ORDER BY kanji_id ASC
            """,
            (user_id, lvl),
        )
        rows = cursor.fetchall()
        cards = {}
        bookmarks = []
        for r in rows:
            kid_str = str(r["kanji_id"])
            cards[kid_str] = {
                "id": r["kanji_id"],
                "status": r["status"],
                "repetitions": r["repetitions"],
                "intervalDays": r["interval_days"],
                "easeFactor": r["ease_factor"],
                "correctCount": r["correct_count"],
                "incorrectCount": r["incorrect_count"],
                "isBookmarked": bool(r["is_bookmarked"]),
                "lastReviewed": r["last_reviewed_at"],
                "nextReview": r["next_review_at"],
            }
            if r["is_bookmarked"]:
                bookmarks.append(r["kanji_id"])

        cursor.execute(
            """
            SELECT id, level, mode, filter_type, chapter_num, queue_json, current_index, completed_count, updated_at
            FROM study_sessions
            WHERE user_id = ? AND level = ? AND is_active = 1
            ORDER BY updated_at DESC LIMIT 1
            """,
            (user_id, lvl),
        )
        sess_row = cursor.fetchone()
        session_data = None
        if sess_row:
            try:
                q_list = json.loads(sess_row["queue_json"])
            except Exception:
                q_list = []
            session_data = {
                "id": sess_row["id"],
                "level": sess_row["level"],
                "mode": sess_row["mode"],
                "filter": sess_row["filter_type"],
                "chapter": sess_row["chapter_num"],
                "queue": q_list,
                "currentIndex": sess_row["current_index"],
                "completed": sess_row["completed_count"],
                "updatedAt": sess_row["updated_at"],
            }

        stats = compute_user_stats(cursor, user_id)

    return {
        "user": dict(user_row),
        "settings": dict(settings_row) if settings_row else {},
        "progress": {
            "level": lvl,
            "cards": cards,
            "bookmarks": bookmarks,
        },
        "session": session_data,
        "stats": stats,
    }


@app.post("/api/auth/google")
@app.post("/auth/google")
def auth_google(req: GoogleAuthRequest):
    """Authenticate with verified Google token and return user, settings, progress, session, and stats."""
    lvl = normalize_level(req.level)
    profile = verify_google_id_token(req.id_token)
    if not profile:
        raise HTTPException(status_code=400, detail="Google Token không hợp lệ hoặc đã hết hạn")

    auth_res = upsert_google_user(profile)
    user_id = auth_res["user"]["id"]

    bundle = fetch_user_bundle(user_id, lvl)
    bundle["token"] = auth_res["token"]
    return bundle


@app.get("/api/auth/me")
@app.get("/auth/me")
def get_current_user(level: Optional[str] = "N3", user_id: str = Depends(get_current_user_id)):
    """Fetch current user profile, preferences, level progress, active session and stats in one call."""
    lvl = normalize_level(level)
    bundle = fetch_user_bundle(user_id, lvl)
    if not bundle or "user" not in bundle:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
    return bundle


@app.post("/api/auth/settings")
@app.post("/auth/settings")
def update_user_settings(req: SettingsUpdateRequest, user_id: str = Depends(get_current_user_id)):
    """Update user study preferences."""
    now_iso = datetime.now(timezone.utc).isoformat()
    updates = []
    params = []

    if req.current_level is not None:
        updates.append("current_level = ?")
        params.append(normalize_level(req.current_level))
    if req.theme is not None:
        if req.theme not in ("light", "dark"):
            raise HTTPException(status_code=400, detail="Theme không hợp lệ")
        updates.append("theme = ?")
        params.append(req.theme)
    if req.shuffle_queue is not None:
        updates.append("shuffle_queue = ?")
        params.append(1 if req.shuffle_queue else 0)
    if req.daily_goal is not None:
        updates.append("daily_goal = ?")
        params.append(max(1, min(500, req.daily_goal)))
    if req.show_furigana is not None:
        updates.append("show_furigana = ?")
        params.append(1 if req.show_furigana else 0)
    if req.auto_audio is not None:
        updates.append("auto_audio = ?")
        params.append(1 if req.auto_audio else 0)

    if updates:
        with db_session() as (conn, cursor):
            updates.append("updated_at = ?")
            params.append(now_iso)
            params.append(user_id)
            sql = f"UPDATE user_settings SET {', '.join(updates)} WHERE user_id = ?"
            cursor.execute(sql, params)
            conn.commit()

    return {"status": "success"}


# -------------------------------------------------------------
# 2. Kanji Progress & Spaced Repetition (SRS)
# -------------------------------------------------------------
@app.get("/api/progress")
@app.get("/progress")
def get_all_progress(level: str = "N3", user_id: str = Depends(get_current_user_id)):
    """Fetch all Kanji card records and bookmarks for this user in the specified level."""
    lvl = normalize_level(level)

    with db_session() as (conn, cursor):
        cursor.execute(
            """
            SELECT kanji_id, status, repetitions, interval_days, ease_factor,
                   correct_count, incorrect_count, is_bookmarked, last_reviewed_at, next_review_at
            FROM user_kanji_progress
            WHERE user_id = ? AND level = ?
            ORDER BY kanji_id ASC
            """,
            (user_id, lvl),
        )
        rows = cursor.fetchall()

    cards = {}
    bookmarks = []
    for r in rows:
        kid_str = str(r["kanji_id"])
        cards[kid_str] = {
            "id": r["kanji_id"],
            "status": r["status"],
            "repetitions": r["repetitions"],
            "intervalDays": r["interval_days"],
            "easeFactor": r["ease_factor"],
            "correctCount": r["correct_count"],
            "incorrectCount": r["incorrect_count"],
            "isBookmarked": bool(r["is_bookmarked"]),
            "lastReviewed": r["last_reviewed_at"],
            "nextReview": r["next_review_at"],
        }
        if r["is_bookmarked"]:
            bookmarks.append(r["kanji_id"])

    return {
        "level": lvl,
        "cards": cards,
        "bookmarks": bookmarks,
    }


@app.post("/api/progress/review")
@app.post("/progress/review")
def review_card(req: CardReviewRequest, user_id: str = Depends(get_current_user_id)):
    """
    Submits a card review result and calculates the next Spaced Repetition interval.
    """
    lvl = normalize_level(req.level)
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    with db_session() as (conn, cursor):
        cursor.execute(
            """
            SELECT status, repetitions, interval_days, ease_factor, correct_count, incorrect_count
            FROM user_kanji_progress
            WHERE user_id = ? AND level = ? AND kanji_id = ?
            """,
            (user_id, lvl, req.kanji_id),
        )
        row = cursor.fetchone()

        if not row:
            status_val = "new"
            reps = 0
            interval = 1
            correct_count = 0
            incorrect_count = 0
        else:
            status_val = row["status"] or "new"
            reps = row["repetitions"] or 0
            interval = row["interval_days"] or 1
            correct_count = row["correct_count"] or 0
            incorrect_count = row["incorrect_count"] or 0

        reps += 1
        interval_before = interval

        if req.is_correct:
            correct_count += 1
            if status_val == "new":
                status_val = "learning"
                interval = 1
            elif status_val == "learning":
                interval = max(1, round(interval * 2))
                if interval >= 8:
                    status_val = "mastered"
            elif status_val == "mastered":
                interval = max(8, round(interval * 2.2))
            next_review_dt = now + timedelta(days=interval)
        else:
            incorrect_count += 1
            status_val = "learning"
            interval = 1
            next_review_dt = now + timedelta(days=1)

        next_review_iso = next_review_dt.isoformat()

        cursor.execute(
            """
            INSERT INTO user_kanji_progress (
                user_id, level, kanji_id, status, repetitions, interval_days, correct_count, incorrect_count,
                last_reviewed_at, next_review_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, level, kanji_id) DO UPDATE SET
                status = excluded.status,
                repetitions = excluded.repetitions,
                interval_days = excluded.interval_days,
                correct_count = excluded.correct_count,
                incorrect_count = excluded.incorrect_count,
                last_reviewed_at = excluded.last_reviewed_at,
                next_review_at = excluded.next_review_at
            """,
            (
                user_id,
                lvl,
                req.kanji_id,
                status_val,
                reps,
                interval,
                correct_count,
                incorrect_count,
                now_iso,
                next_review_iso,
            ),
        )

        cursor.execute(
            """
            INSERT INTO study_logs (user_id, level, kanji_id, mode, is_correct, interval_before, interval_after, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, lvl, req.kanji_id, req.mode or "flashcard", 1 if req.is_correct else 0, interval_before, interval, now_iso),
        )

        conn.commit()
        stats = compute_user_stats(cursor, user_id)

    return {
        "level": lvl,
        "kanji_id": req.kanji_id,
        "status": status_val,
        "repetitions": reps,
        "intervalDays": interval,
        "nextReview": next_review_iso,
        "correctCount": correct_count,
        "incorrectCount": incorrect_count,
        "currentStreak": stats["currentStreak"],
        "bestStreak": stats["bestStreak"],
        "todayReviews": stats["todayReviews"],
        "totalReviews": stats["totalReviews"],
    }


@app.post("/api/progress/bookmark")
@app.post("/progress/bookmark")
def toggle_bookmark(req: BookmarkToggleRequest, user_id: str = Depends(get_current_user_id)):
    """Toggle star / bookmark for a specific kanji."""
    lvl = normalize_level(req.level)

    with db_session() as (conn, cursor):
        cursor.execute(
            "SELECT is_bookmarked FROM user_kanji_progress WHERE user_id = ? AND level = ? AND kanji_id = ?",
            (user_id, lvl, req.kanji_id),
        )
        row = cursor.fetchone()
        current_state = row["is_bookmarked"] if row else 0
        new_state = 0 if current_state else 1

        cursor.execute(
            """
            INSERT INTO user_kanji_progress (user_id, level, kanji_id, is_bookmarked)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, level, kanji_id) DO UPDATE SET is_bookmarked = excluded.is_bookmarked
            """,
            (user_id, lvl, req.kanji_id, new_state),
        )
        conn.commit()

    return {"level": lvl, "kanji_id": req.kanji_id, "is_bookmarked": bool(new_state)}


@app.post("/api/progress/reset")
@app.post("/progress/reset")
def reset_progress(req: ResetProgressRequest, user_id: str = Depends(get_current_user_id)):
    """Resets all cloud progress and deactivates ongoing study session for the requested JLPT level."""
    lvl = normalize_level(req.level)

    with db_session() as (conn, cursor):
        cursor.execute("DELETE FROM user_kanji_progress WHERE user_id = ? AND level = ?", (user_id, lvl))
        cursor.execute("UPDATE study_sessions SET is_active = 0 WHERE user_id = ? AND level = ?", (user_id, lvl))
        conn.commit()

    return {"status": "reset", "level": lvl}


# -------------------------------------------------------------
# 3. Study Session (Resume across devices via UPSERT)
# -------------------------------------------------------------
@app.get("/api/session/current")
@app.get("/session/current")
def get_current_session(level: Optional[str] = None, user_id: str = Depends(get_current_user_id)):
    """Retrieves any active/unfinished study session."""
    lvl = normalize_level(level) if level else None

    with db_session() as (conn, cursor):
        if lvl:
            cursor.execute(
                """
                SELECT id, level, mode, filter_type, chapter_num, queue_json, current_index, completed_count, updated_at
                FROM study_sessions
                WHERE user_id = ? AND level = ? AND is_active = 1
                ORDER BY updated_at DESC LIMIT 1
                """,
                (user_id, lvl),
            )
        else:
            cursor.execute(
                """
                SELECT id, level, mode, filter_type, chapter_num, queue_json, current_index, completed_count, updated_at
                FROM study_sessions
                WHERE user_id = ? AND is_active = 1
                ORDER BY updated_at DESC LIMIT 1
                """,
                (user_id,),
            )
        row = cursor.fetchone()

    if not row:
        return {"session": None}

    return {
        "session": {
            "id": row["id"],
            "level": row["level"],
            "mode": row["mode"],
            "filter": row["filter_type"],
            "filter_type": row["filter_type"],
            "chapter": row["chapter_num"],
            "chapter_num": row["chapter_num"],
            "queue": json.loads(row["queue_json"]),
            "currentIndex": row["current_index"],
            "current_index": row["current_index"],
            "completed": row["completed_count"],
            "completed_count": row["completed_count"],
            "updatedAt": row["updated_at"],
        }
    }


@app.post("/api/session/save")
@app.post("/session/save")
def save_session(req: SessionSaveRequest, user_id: str = Depends(get_current_user_id)):
    """Saves or updates ongoing study session state cleanly via single-row UPSERT per (user, level)."""
    lvl = normalize_level(req.level)
    now_iso = datetime.now(timezone.utc).isoformat()
    session_id = f"sess_{user_id}_{lvl}"
    q_json = json.dumps(req.queue, ensure_ascii=False)

    with db_session() as (conn, cursor):
        # Remove any legacy multi-row timestamps for this (user, level)
        cursor.execute(
            "DELETE FROM study_sessions WHERE user_id = ? AND level = ? AND id != ?",
            (user_id, lvl, session_id),
        )
        cursor.execute(
            """
            INSERT INTO study_sessions (
                id, user_id, level, mode, filter_type, chapter_num, queue_json,
                current_index, completed_count, is_active, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
            ON CONFLICT(id) DO UPDATE SET
                mode = excluded.mode,
                filter_type = excluded.filter_type,
                chapter_num = excluded.chapter_num,
                queue_json = excluded.queue_json,
                current_index = excluded.current_index,
                completed_count = excluded.completed_count,
                is_active = 1,
                updated_at = excluded.updated_at
            """,
            (
                session_id,
                user_id,
                lvl,
                req.mode,
                req.filter_type,
                req.chapter_num,
                q_json,
                req.current_index,
                req.completed_count,
                now_iso,
            ),
        )
        conn.commit()

    return {"status": "saved", "session_id": session_id}


@app.post("/api/session/complete")
@app.post("/session/complete")
def complete_session(level: Optional[str] = None, user_id: str = Depends(get_current_user_id)):
    """Marks active study session completed for the specified level (or all levels if omitted)."""
    lvl = normalize_level(level) if level else None

    with db_session() as (conn, cursor):
        if lvl:
            cursor.execute(
                "UPDATE study_sessions SET is_active = 0 WHERE user_id = ? AND level = ?",
                (user_id, lvl),
            )
        else:
            cursor.execute("UPDATE study_sessions SET is_active = 0 WHERE user_id = ?", (user_id,))
        conn.commit()

    return {"status": "completed", "level": lvl}


# -------------------------------------------------------------
# 4. Import / Merge Local Offline Data
# -------------------------------------------------------------
@app.post("/api/sync/import-local")
@app.post("/sync/import-local")
def import_local_progress(req: ImportLocalRequest, user_id: str = Depends(get_current_user_id)):
    """
    Seamlessly merges offline Guest / localStorage cards into the authenticated account.
    Uses dialect-aware GREATEST (PostgreSQL) / MAX (SQLite).
    """
    lvl = normalize_level(req.level)

    # Validate & sanitize entries strictly in Python before SQL execution
    cleaned_cards = []
    for kid_str, card in req.cards.items():
        if not isinstance(card, dict):
            continue
        try:
            kid = int(kid_str)
            reps = max(0, int(card.get("repetitions") or 0))
            interval = max(0, int(card.get("intervalDays") or 1))
            correct = max(0, int(card.get("correctCount") or 0))
            incorrect = max(0, int(card.get("incorrectCount") or 0))
        except (TypeError, ValueError):
            continue
        status_val = str(card.get("status") or "new")
        if status_val not in VALID_CARD_STATUSES:
            status_val = "new"
        last_rev = card.get("lastReviewed")
        next_rev = card.get("nextReview")
        cleaned_cards.append((user_id, lvl, kid, status_val, reps, interval, correct, incorrect, last_rev, next_rev))

    cleaned_bookmarks = []
    if req.bookmarks:
        for b_kid in req.bookmarks:
            try:
                cleaned_bookmarks.append(int(b_kid))
            except (TypeError, ValueError):
                continue

    with db_session() as (conn, cursor):
        max_fn = "GREATEST" if is_pg_conn(conn) else "MAX"
        upsert_card_sql = f"""
            INSERT INTO user_kanji_progress (
                user_id, level, kanji_id, status, repetitions, interval_days, correct_count, incorrect_count,
                last_reviewed_at, next_review_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, level, kanji_id) DO UPDATE SET
                status = CASE WHEN excluded.repetitions > user_kanji_progress.repetitions THEN excluded.status ELSE user_kanji_progress.status END,
                repetitions = {max_fn}(user_kanji_progress.repetitions, excluded.repetitions),
                interval_days = {max_fn}(user_kanji_progress.interval_days, excluded.interval_days),
                correct_count = {max_fn}(user_kanji_progress.correct_count, excluded.correct_count),
                incorrect_count = {max_fn}(user_kanji_progress.incorrect_count, excluded.incorrect_count),
                last_reviewed_at = COALESCE(excluded.last_reviewed_at, user_kanji_progress.last_reviewed_at),
                next_review_at = COALESCE(excluded.next_review_at, user_kanji_progress.next_review_at)
        """
        if cleaned_cards:
            cursor.executemany(upsert_card_sql, cleaned_cards)

        if cleaned_bookmarks:
            cursor.executemany(
                """
                INSERT INTO user_kanji_progress (user_id, level, kanji_id, is_bookmarked)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(user_id, level, kanji_id) DO UPDATE SET is_bookmarked = 1
                """,
                [(user_id, lvl, b_kid) for b_kid in cleaned_bookmarks],
            )

        if req.session and req.session.get("active"):
            sess = req.session
            sess_id = f"sess_{user_id}_{lvl}"
            q_json = json.dumps(sess.get("queue", []), ensure_ascii=False)
            now_iso = datetime.now(timezone.utc).isoformat()
            cur_idx = int(sess.get("currentIndex", sess.get("current_index", 0)) or 0)
            comp_cnt = int(sess.get("completed", sess.get("completed_count", 0)) or 0)
            cursor.execute(
                "DELETE FROM study_sessions WHERE user_id = ? AND level = ? AND id != ?",
                (user_id, lvl, sess_id),
            )
            cursor.execute(
                """
                INSERT INTO study_sessions (
                    id, user_id, level, mode, filter_type, chapter_num, queue_json, current_index, completed_count, is_active, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                ON CONFLICT(id) DO UPDATE SET
                    mode = excluded.mode,
                    filter_type = excluded.filter_type,
                    chapter_num = excluded.chapter_num,
                    queue_json = excluded.queue_json,
                    current_index = excluded.current_index,
                    completed_count = excluded.completed_count,
                    is_active = 1,
                    updated_at = excluded.updated_at
                """,
                (
                    sess_id,
                    user_id,
                    lvl,
                    sess.get("mode", "flashcard"),
                    sess.get("filter", sess.get("filter_type", "all")),
                    sess.get("chapter", sess.get("chapter_num")),
                    q_json,
                    cur_idx,
                    comp_cnt,
                    now_iso,
                ),
            )

        conn.commit()

    return {"status": "success", "level": lvl, "merged_cards": len(cleaned_cards)}


# -------------------------------------------------------------
# 5. Dashboard Summary Stats
# -------------------------------------------------------------
@app.get("/api/stats/dashboard")
@app.get("/stats/dashboard")
def get_dashboard_stats(level: str = "N3", user_id: str = Depends(get_current_user_id)):
    """Computes accurate dashboard aggregates and study streak for the user in the specified level."""
    lvl = normalize_level(level)
    now_iso = datetime.now(timezone.utc).isoformat()

    with db_session() as (conn, cursor):
        cursor.execute(
            """
            SELECT
                COUNT(CASE WHEN status = 'mastered' THEN 1 END) as mastered_count,
                COUNT(CASE WHEN status = 'learning' THEN 1 END) as learning_count,
                COUNT(CASE WHEN status = 'new' THEN 1 END) as new_count,
                COUNT(CASE WHEN status IN ('learning', 'mastered') AND next_review_at IS NOT NULL AND next_review_at <= ? THEN 1 END) as due_count,
                SUM(correct_count) as total_correct,
                SUM(incorrect_count) as total_incorrect
            FROM user_kanji_progress
            WHERE user_id = ? AND level = ?
            """,
            (now_iso, user_id, lvl),
        )
        row = cursor.fetchone()
        stats = compute_user_stats(cursor, user_id)

    return {
        "level": lvl,
        "mastered": row["mastered_count"] or 0,
        "learning": row["learning_count"] or 0,
        "new": row["new_count"] or 0,
        "dueCount": row["due_count"] or 0,
        "totalCorrect": row["total_correct"] or 0,
        "totalIncorrect": row["total_incorrect"] or 0,
        "currentStreak": stats["currentStreak"],
        "bestStreak": stats["bestStreak"],
        "todayReviews": stats["todayReviews"],
        "totalReviews": stats["totalReviews"],
    }


# -------------------------------------------------------------
# 6. Static File Delivery (Serving Web App)
# -------------------------------------------------------------
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(WORKSPACE_DIR, "index.html"))


@app.get("/kanji-data.js")
def serve_kanji_data():
    return FileResponse(os.path.join(WORKSPACE_DIR, "kanji-data.js"))


@app.get("/db.json")
def serve_db_json():
    return FileResponse(os.path.join(WORKSPACE_DIR, "db.json"))


@app.get("/data/{filename}")
def serve_data_json(filename: str):
    if ".." in filename or not re.fullmatch(r"[a-zA-Z0-9._-]+\.json", filename):
        raise HTTPException(status_code=400, detail="Tên file không hợp lệ")

    data_dir = (Path(WORKSPACE_DIR) / "data").resolve()
    target = (data_dir / filename).resolve()
    if target.parent != data_dir or not target.is_file():
        raise HTTPException(status_code=404, detail="File không tồn tại")

    return FileResponse(str(target))


@app.get("/components/{filename}")
def serve_component_asset(filename: str):
    if ".." in filename or not re.fullmatch(r"[a-zA-Z0-9._-]+\.(css|js)", filename):
        raise HTTPException(status_code=400, detail="Tên file không hợp lệ")

    comp_dir = (Path(WORKSPACE_DIR) / "components").resolve()
    target = (comp_dir / filename).resolve()
    if target.parent != comp_dir or not target.is_file():
        raise HTTPException(status_code=404, detail="File không tồn tại")

    return FileResponse(str(target))


# Run using standard uvicorn entrypoint
if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    print(f"Starting Kanji Master Production Server on http://0.0.0.0:{port}")
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
