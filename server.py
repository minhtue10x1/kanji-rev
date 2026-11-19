# -*- coding: utf-8 -*-
"""
High-Performance FastAPI Server for Kanji Master Multi-Level (N5 - N1).
Provides Google OAuth2 authentication, multi-level SRS sync, and static web serving.
"""

import os
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Depends, Header, status, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import get_db, init_database
from auth import verify_google_id_token, upsert_google_user, decode_jwt

# Initialize database schema on startup safely
try:
    init_database()
except Exception as e:
    print(f"Warning: Deferred database initialization on startup: {e}")

app = FastAPI(title="Kanji Master Full Multi-Level API", version="2.0.0")

# Enable CORS for cross-origin or local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
        "google_client_id": os.environ.get("GOOGLE_CLIENT_ID", "")
    }

# -------------------------------------------------------------
# Dependency: Extract Current Authenticated User
# -------------------------------------------------------------
def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Chưa đăng nhập (Thiếu Token)")

    token = authorization.replace("Bearer ", "").strip()
    payload = decode_jwt(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Phiên đăng nhập hết hạn hoặc không hợp lệ")

    return payload["sub"]


# -------------------------------------------------------------
# Pydantic Request Models
# -------------------------------------------------------------
class GoogleAuthRequest(BaseModel):
    id_token: str

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
    queue: List[int]
    current_index: int
    completed_count: int

class ImportLocalRequest(BaseModel):
    level: Optional[str] = "N3"
    cards: Dict[str, Any]
    bookmarks: Optional[List[int]] = None


# -------------------------------------------------------------
# 1. Authentication & Public Config Endpoints
# -------------------------------------------------------------
@app.get("/api/config")
@app.get("/config")
def get_public_config():
    """Public environment configuration for frontend clients."""
    return {
        "google_client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
        "environment": "production" if os.environ.get("VERCEL") else "development"
    }

@app.post("/api/auth/google")
@app.post("/auth/google")
def auth_google(req: GoogleAuthRequest):
    """Authenticate with Google ID Token from Google Identity Services."""
    profile = verify_google_id_token(req.id_token)
    if not profile:
        raise HTTPException(status_code=400, detail="Google Token không hợp lệ hoặc đã hết hạn")

    result = upsert_google_user(profile)
    return result

@app.get("/api/auth/me")
@app.get("/auth/me")
def get_current_user(user_id: str = Depends(get_current_user_id)):
    """Fetch current user profile and preferences."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, email, name, avatar_url, created_at, last_login_at FROM users WHERE id = ?", (user_id,))
    user_row = cursor.fetchone()
    if not user_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")

    cursor.execute("SELECT * FROM user_settings WHERE user_id = ?", (user_id,))
    settings_row = cursor.fetchone()

    conn.close()
    return {
        "user": dict(user_row),
        "settings": dict(settings_row) if settings_row else {}
    }

@app.post("/api/auth/settings")
@app.post("/auth/settings")
def update_user_settings(req: SettingsUpdateRequest, user_id: str = Depends(get_current_user_id)):
    """Update user study preferences."""
    conn = get_db()
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()

    updates = []
    params = []
    if req.current_level is not None:
        updates.append("current_level = ?")
        params.append(req.current_level)
    if req.theme is not None:
        updates.append("theme = ?")
        params.append(req.theme)
    if req.shuffle_queue is not None:
        updates.append("shuffle_queue = ?")
        params.append(1 if req.shuffle_queue else 0)
    if req.daily_goal is not None:
        updates.append("daily_goal = ?")
        params.append(req.daily_goal)
    if req.show_furigana is not None:
        updates.append("show_furigana = ?")
        params.append(1 if req.show_furigana else 0)
    if req.auto_audio is not None:
        updates.append("auto_audio = ?")
        params.append(1 if req.auto_audio else 0)

    if updates:
        updates.append("updated_at = ?")
        params.append(now_iso)
        params.append(user_id)
        sql = f"UPDATE user_settings SET {', '.join(updates)} WHERE user_id = ?"
        cursor.execute(sql, params)
        conn.commit()

    conn.close()
    return {"status": "success"}


# -------------------------------------------------------------
# 2. Kanji Progress & Spaced Repetition (SRS)
# -------------------------------------------------------------
@app.get("/api/progress")
@app.get("/progress")
def get_all_progress(level: str = "N3", user_id: str = Depends(get_current_user_id)):
    """Fetch all Kanji card records and bookmarks for this user in the specified level."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT kanji_id, status, repetitions, interval_days, ease_factor,
               correct_count, incorrect_count, is_bookmarked, last_reviewed_at, next_review_at
        FROM user_kanji_progress
        WHERE user_id = ? AND level = ?
        ORDER BY kanji_id ASC
    """, (user_id, level.upper()))
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
            "nextReview": r["next_review_at"]
        }
        if r["is_bookmarked"]:
            bookmarks.append(r["kanji_id"])

    conn.close()
    return {
        "level": level.upper(),
        "cards": cards,
        "bookmarks": bookmarks
    }

@app.post("/api/progress/review")
@app.post("/progress/review")
def review_card(req: CardReviewRequest, user_id: str = Depends(get_current_user_id)):
    """
    Submits a card review result and calculates the next Spaced Repetition interval.
    SM-2 inspired exponential progression.
    """
    conn = get_db()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    lvl = (req.level or "N3").upper()

    cursor.execute("""
        SELECT status, repetitions, interval_days, ease_factor, correct_count, incorrect_count
        FROM user_kanji_progress
        WHERE user_id = ? AND level = ? AND kanji_id = ?
    """, (user_id, lvl, req.kanji_id))
    row = cursor.fetchone()

    if not row:
        status_val = "new"
        reps = 0
        interval = 1
        correct_count = 0
        incorrect_count = 0
    else:
        status_val = row["status"]
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
            interval = round(interval * 2.2)
        next_review_dt = now + timedelta(days=interval)
    else:
        incorrect_count += 1
        status_val = "learning"
        interval = 1
        next_review_dt = now + timedelta(days=1)

    next_review_iso = next_review_dt.isoformat()

    cursor.execute("""
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
    """, (user_id, lvl, req.kanji_id, status_val, reps, interval, correct_count, incorrect_count, now_iso, next_review_iso))

    # Log review for analytics
    cursor.execute("""
        INSERT INTO study_logs (user_id, level, kanji_id, mode, is_correct, interval_before, interval_after, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, lvl, req.kanji_id, req.mode, 1 if req.is_correct else 0, interval_before, interval, now_iso))

    conn.commit()
    conn.close()

    return {
        "level": lvl,
        "kanji_id": req.kanji_id,
        "status": status_val,
        "repetitions": reps,
        "intervalDays": interval,
        "nextReview": next_review_iso,
        "correctCount": correct_count,
        "incorrectCount": incorrect_count
    }

@app.post("/api/progress/bookmark")
@app.post("/progress/bookmark")
def toggle_bookmark(req: BookmarkToggleRequest, user_id: str = Depends(get_current_user_id)):
    """Toggle star / bookmark for a specific kanji."""
    conn = get_db()
    cursor = conn.cursor()
    lvl = (req.level or "N3").upper()

    cursor.execute("SELECT is_bookmarked FROM user_kanji_progress WHERE user_id = ? AND level = ? AND kanji_id = ?", 
                   (user_id, lvl, req.kanji_id))
    row = cursor.fetchone()
    current_state = row["is_bookmarked"] if row else 0
    new_state = 0 if current_state else 1

    cursor.execute("""
        INSERT INTO user_kanji_progress (user_id, level, kanji_id, is_bookmarked)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, level, kanji_id) DO UPDATE SET is_bookmarked = excluded.is_bookmarked
    """, (user_id, lvl, req.kanji_id, new_state))

    conn.commit()
    conn.close()

    return {"level": lvl, "kanji_id": req.kanji_id, "is_bookmarked": bool(new_state)}


# -------------------------------------------------------------
# 3. Study Session (Resume across devices)
# -------------------------------------------------------------
@app.get("/api/session/current")
@app.get("/session/current")
def get_current_session(level: Optional[str] = None, user_id: str = Depends(get_current_user_id)):
    """Retrieves any active/unfinished study session."""
    conn = get_db()
    cursor = conn.cursor()

    if level:
        cursor.execute("""
            SELECT id, level, mode, filter_type, chapter_num, queue_json, current_index, completed_count, updated_at
            FROM study_sessions
            WHERE user_id = ? AND level = ? AND is_active = 1
            ORDER BY updated_at DESC LIMIT 1
        """, (user_id, level.upper()))
    else:
        cursor.execute("""
            SELECT id, level, mode, filter_type, chapter_num, queue_json, current_index, completed_count, updated_at
            FROM study_sessions
            WHERE user_id = ? AND is_active = 1
            ORDER BY updated_at DESC LIMIT 1
        """, (user_id,))
    row = cursor.fetchone()
    conn.close()

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
            "updatedAt": row["updated_at"]
        }
    }

@app.post("/api/session/save")
@app.post("/session/save")
def save_session(req: SessionSaveRequest, user_id: str = Depends(get_current_user_id)):
    """Saves or updates ongoing study session state."""
    conn = get_db()
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    lvl = (req.level or "N3").upper()

    # Deactivate existing sessions for this user and level
    cursor.execute("UPDATE study_sessions SET is_active = 0 WHERE user_id = ? AND level = ?", (user_id, lvl))

    session_id = f"sess_{user_id[:8]}_{lvl}_{int(datetime.now().timestamp())}"
    cursor.execute("""
        INSERT INTO study_sessions (
            id, user_id, level, mode, filter_type, chapter_num, queue_json,
            current_index, completed_count, is_active, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
    """, (session_id, user_id, lvl, req.mode, req.filter_type, req.chapter_num, 
          json.dumps(req.queue), req.current_index, req.completed_count, now_iso))

    conn.commit()
    conn.close()
    return {"status": "saved", "session_id": session_id}

@app.post("/api/session/complete")
@app.post("/session/complete")
def complete_session(level: Optional[str] = None, user_id: str = Depends(get_current_user_id)):
    """Marks active study session completed."""
    conn = get_db()
    cursor = conn.cursor()
    if level:
        cursor.execute("UPDATE study_sessions SET is_active = 0 WHERE user_id = ? AND level = ?", (user_id, level.upper()))
    else:
        cursor.execute("UPDATE study_sessions SET is_active = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return {"status": "completed"}


# -------------------------------------------------------------
# 4. Import / Merge Local Offline Data
# -------------------------------------------------------------
@app.post("/api/sync/import-local")
@app.post("/sync/import-local")
def import_local_progress(req: ImportLocalRequest, user_id: str = Depends(get_current_user_id)):
    """
    Seamlessly merges offline Guest / localStorage cards into the newly logged-in account.
    """
    conn = get_db()
    cursor = conn.cursor()
    lvl = (req.level or "N3").upper()

    imported_count = 0
    for kid_str, card in req.cards.items():
        try:
            kid = int(kid_str)
            status_val = card.get("status", "new")
            reps = card.get("repetitions", 0)
            interval = card.get("intervalDays", 1)
            correct = card.get("correctCount", 0)
            incorrect = card.get("incorrectCount", 0)
            last_rev = card.get("lastReviewed")
            next_rev = card.get("nextReview")

            cursor.execute("""
                INSERT INTO user_kanji_progress (
                    user_id, level, kanji_id, status, repetitions, interval_days, correct_count, incorrect_count,
                    last_reviewed_at, next_review_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, level, kanji_id) DO UPDATE SET
                    status = CASE WHEN excluded.repetitions > user_kanji_progress.repetitions THEN excluded.status ELSE user_kanji_progress.status END,
                    repetitions = MAX(user_kanji_progress.repetitions, excluded.repetitions),
                    interval_days = MAX(user_kanji_progress.interval_days, excluded.interval_days),
                    correct_count = MAX(user_kanji_progress.correct_count, excluded.correct_count),
                    incorrect_count = MAX(user_kanji_progress.incorrect_count, excluded.incorrect_count),
                    last_reviewed_at = COALESCE(excluded.last_reviewed_at, user_kanji_progress.last_reviewed_at),
                    next_review_at = COALESCE(excluded.next_review_at, user_kanji_progress.next_review_at)
            """, (user_id, lvl, kid, status_val, reps, interval, correct, incorrect, last_rev, next_rev))
            imported_count += 1
        except Exception:
            continue

    if req.bookmarks:
        for b_kid in req.bookmarks:
            cursor.execute("""
                UPDATE user_kanji_progress SET is_bookmarked = 1 WHERE user_id = ? AND level = ? AND kanji_id = ?
            """, (user_id, lvl, b_kid))

    conn.commit()
    conn.close()
    return {"status": "success", "level": lvl, "merged_cards": imported_count}


# -------------------------------------------------------------
# 5. Dashboard Summary Stats
# -------------------------------------------------------------
@app.get("/api/stats/dashboard")
@app.get("/stats/dashboard")
def get_dashboard_stats(level: str = "N3", user_id: str = Depends(get_current_user_id)):
    """Computes accurate dashboard aggregates for the user in the specified level."""
    conn = get_db()
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    lvl = level.upper()

    cursor.execute("""
        SELECT 
            COUNT(CASE WHEN status = 'mastered' THEN 1 END) as mastered_count,
            COUNT(CASE WHEN status = 'learning' THEN 1 END) as learning_count,
            COUNT(CASE WHEN status = 'new' THEN 1 END) as new_count,
            COUNT(CASE WHEN status IN ('learning', 'mastered') AND next_review_at IS NOT NULL AND next_review_at <= ? THEN 1 END) as due_count,
            SUM(correct_count) as total_correct,
            SUM(incorrect_count) as total_incorrect
        FROM user_kanji_progress
        WHERE user_id = ? AND level = ?
    """, (now_iso, user_id, lvl))
    row = cursor.fetchone()

    conn.close()
    return {
        "level": lvl,
        "mastered": row["mastered_count"] or 0,
        "learning": row["learning_count"] or 0,
        "new": row["new_count"] or 0,
        "dueCount": row["due_count"] or 0,
        "totalCorrect": row["total_correct"] or 0,
        "totalIncorrect": row["total_incorrect"] or 0
    }


# -------------------------------------------------------------
# 6. Static File Delivery (Serving Web App)
# -------------------------------------------------------------
WORKSPACE_DIR = os.path.dirname(__file__)

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
    file_path = os.path.join(WORKSPACE_DIR, "data", filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="File không tồn tại")

# Run using standard uvicorn entrypoint
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting Kanji Master Production Server on http://0.0.0.0:{port}")
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
