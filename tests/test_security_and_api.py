# -*- coding: utf-8 -*-
import os
import sys
import json
import time
import hmac
import hashlib
import base64
import asyncio
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

_TMP_DIR = tempfile.TemporaryDirectory()
os.environ["KANJI_DB_PATH"] = str(Path(_TMP_DIR.name) / "test_kanji.db")
os.environ["JWT_SECRET_KEY"] = "test-suite-strong-jwt-secret-key-2026"
os.environ["GOOGLE_CLIENT_ID"] = "expected-client-id.apps.googleusercontent.com"

import database  # noqa: E402
import auth      # noqa: E402
import server    # noqa: E402


async def asgi_request(app, method: str, path: str, headers=None, body: bytes = b"", query: str = ""):
    raw_headers = []
    for k, v in (headers or {}).items():
        raw_headers.append((k.lower().encode("latin-1"), v.encode("latin-1")))
    if body and not any(k == b"content-length" for k, _ in raw_headers):
        raw_headers.append((b"content-length", str(len(body)).encode("latin-1")))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method.upper(),
        "scheme": "https",
        "path": path,
        "raw_path": path.encode("latin-1"),
        "query_string": query.encode("latin-1"),
        "headers": raw_headers,
        "client": ("127.0.0.1", 12345),
        "server": ("kanji-rev.vercel.app", 443),
    }

    sent_body = False
    async def receive():
        nonlocal sent_body
        if not sent_body:
            sent_body = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    status_code = 500
    resp_headers = {}
    resp_chunks = []

    async def send(message):
        nonlocal status_code
        if message["type"] == "http.response.start":
            status_code = message["status"]
            for hk, hv in message.get("headers", []):
                resp_headers[hk.decode("latin-1").lower()] = hv.decode("latin-1")
        elif message["type"] == "http.response.body":
            resp_chunks.append(message.get("body", b""))

    await app(scope, receive, send)
    raw = b"".join(resp_chunks)
    return status_code, resp_headers, raw


def call_api(method: str, path: str, headers=None, json_data=None, query: str = ""):
    body = b""
    hdrs = dict(headers or {})
    if json_data is not None:
        body = json.dumps(json_data).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    status_code, resp_headers, raw = asyncio.run(asgi_request(server.app, method, path, hdrs, body, query))
    parsed = None
    if raw and "application/json" in resp_headers.get("content-type", ""):
        parsed = json.loads(raw.decode("utf-8"))
    return status_code, resp_headers, parsed, raw


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


class _FakeResponse:
    def __init__(self, status: int, payload: dict):
        self.status = status
        self._raw = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class SecurityAndApiTests(unittest.TestCase):
    def setUp(self):
        db_file = Path(os.environ["KANJI_DB_PATH"])
        if db_file.exists():
            db_file.unlink()
        database.init_database(force=True)

    def test_auth_rejects_email_and_mock_backdoors(self):
        self.assertIsNone(auth.verify_google_id_token("email_victim@gmail.com"))
        self.assertIsNone(auth.verify_google_id_token("mock_victim@gmail.com"))
        self.assertIsNone(auth.verify_google_id_token(""))
        self.assertIsNone(auth.verify_google_id_token("   "))

        with patch.dict(os.environ, {"ALLOW_DEV_MOCK_AUTH": "true", "VERCEL": "1"}):
            self.assertIsNone(auth.verify_google_id_token("mock_victim@gmail.com"))

        with patch.dict(os.environ, {"ALLOW_DEV_MOCK_AUTH": "true"}, clear=False):
            os.environ.pop("VERCEL", None)
            profile = auth.verify_google_id_token("mock_devuser@gmail.com")
            self.assertIsNotNone(profile)
            self.assertEqual(profile["email"], "devuser@gmail.com")

        status_code, _, body, _ = call_api(
            "POST",
            "/api/auth/google",
            json_data={"id_token": "email_victim@gmail.com", "level": "N3"},
        )
        self.assertEqual(status_code, 400)
        self.assertIn("detail", body)

    def test_jwt_rejects_old_secret_alg_none_and_missing_or_expired_exp(self):
        now = int(time.time())
        valid_token = auth.create_jwt({"sub": "u1", "email": "a@gmail.com", "exp": now + 3600})
        self.assertEqual(auth.decode_jwt(valid_token)["sub"], "u1")

        # Token signed with old hardcoded secret must be rejected
        old_secret = b"kanji-rev-production-secret-key-jlpt-n3-2026"
        h = _b64u(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
        p = _b64u(json.dumps({"sub": "u1", "exp": now + 3600}, separators=(",", ":")).encode())
        sig = _b64u(hmac.new(old_secret, f"{h}.{p}".encode(), hashlib.sha256).digest())
        self.assertIsNone(auth.decode_jwt(f"{h}.{p}.{sig}"))

        # alg=none rejected even if HMAC matches
        h_none = _b64u(json.dumps({"alg": "none", "typ": "JWT"}, separators=(",", ":")).encode())
        sig_none = _b64u(
            hmac.new(auth.get_jwt_secret().encode(), f"{h_none}.{p}".encode(), hashlib.sha256).digest()
        )
        self.assertIsNone(auth.decode_jwt(f"{h_none}.{p}.{sig_none}"))

        # Expired token rejected
        expired = auth.create_jwt({"sub": "u1", "exp": now - 10})
        self.assertIsNone(auth.decode_jwt(expired))

        # Missing exp rejected
        no_exp = auth.create_jwt({"sub": "u1"})
        self.assertIsNone(auth.decode_jwt(no_exp))

        # Production without JWT_SECRET_KEY or POSTGRES_URL raises
        with patch.dict(os.environ, {"VERCEL": "1", "JWT_SECRET_KEY": ""}):
            with patch.object(auth, "get_postgres_url", return_value=None):
                with self.assertRaises(RuntimeError):
                    auth.get_jwt_secret()

    def test_google_id_token_checks_aud_and_email_verified(self):
        fake_jwt = "aaa.bbb.ccc"

        def mock_urlopen_wrong_aud(req, timeout=8):
            return _FakeResponse(
                200,
                {
                    "sub": "g-123",
                    "email": "user@gmail.com",
                    "email_verified": "true",
                    "iss": "https://accounts.google.com",
                    "aud": "wrong-client-id.apps.googleusercontent.com",
                },
            )

        with patch("urllib.request.urlopen", side_effect=mock_urlopen_wrong_aud):
            self.assertIsNone(auth.verify_google_id_token(fake_jwt))

        def mock_urlopen_unverified(req, timeout=8):
            return _FakeResponse(
                200,
                {
                    "sub": "g-123",
                    "email": "user@gmail.com",
                    "email_verified": "false",
                    "iss": "https://accounts.google.com",
                    "aud": "expected-client-id.apps.googleusercontent.com",
                },
            )

        with patch("urllib.request.urlopen", side_effect=mock_urlopen_unverified):
            self.assertIsNone(auth.verify_google_id_token(fake_jwt))

        def mock_urlopen_valid(req, timeout=8):
            return _FakeResponse(
                200,
                {
                    "sub": "g-123",
                    "email": "user@gmail.com",
                    "name": "Test User",
                    "picture": "https://example.com/p.png",
                    "email_verified": "true",
                    "iss": "https://accounts.google.com",
                    "aud": "expected-client-id.apps.googleusercontent.com",
                },
            )

        with patch("urllib.request.urlopen", side_effect=mock_urlopen_valid):
            prof = auth.verify_google_id_token(fake_jwt)
            self.assertIsNotNone(prof)
            self.assertEqual(prof["sub"], "g-123")
            self.assertEqual(prof["email"], "user@gmail.com")

    def test_upsert_does_not_preseed_and_session_upsert_no_duplicates(self):
        res = auth.upsert_google_user({
            "sub": "sub-1",
            "email": "learner@gmail.com",
            "name": "Learner",
            "picture": "https://example.com/a.png",
        })
        user_id = res["user"]["id"]
        token = res["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Verify 0 pre-seeded progress rows
        with database.db_session() as (conn, cursor):
            cursor.execute("SELECT COUNT(*) AS cnt FROM user_kanji_progress WHERE user_id = ?", (user_id,))
            self.assertEqual(cursor.fetchone()["cnt"], 0)

        # Save sessions repeatedly in same second + for N4 -> zero PK collision, 1 row per (user, level)
        for idx in range(3):
            code, _, body, _ = call_api(
                "POST",
                "/api/session/save",
                headers=headers,
                json_data={
                    "level": "N3",
                    "mode": "quiz",
                    "filter_type": "chapter",
                    "chapter_num": 1,
                    "queue": [{"id": 1, "word": "起きる", "reading": "おきる"}],
                    "current_index": idx,
                    "completed_count": idx,
                },
            )
            self.assertEqual(code, 200)
            self.assertEqual(body["status"], "saved")

        code_n4, _, _, _ = call_api(
            "POST",
            "/api/session/save",
            headers=headers,
            json_data={
                "level": "N4",
                "mode": "flashcard",
                "filter_type": "all",
                "queue": [1, 2, 3],
                "current_index": 1,
                "completed_count": 1,
            },
        )
        self.assertEqual(code_n4, 200)

        with database.db_session() as (conn, cursor):
            cursor.execute("SELECT COUNT(*) AS cnt FROM study_sessions WHERE user_id = ? AND level = 'N3'", (user_id,))
            self.assertEqual(cursor.fetchone()["cnt"], 1)

        # Completing N3 must keep N4 active
        code_comp, _, _, _ = call_api("POST", "/api/session/complete", headers=headers, query="level=N3")
        self.assertEqual(code_comp, 200)

        _, _, sess_n3, _ = call_api("GET", "/api/session/current", headers=headers, query="level=N3")
        _, _, sess_n4, _ = call_api("GET", "/api/session/current", headers=headers, query="level=N4")
        self.assertIsNone(sess_n3["session"])
        self.assertIsNotNone(sess_n4["session"])
        self.assertEqual(sess_n4["session"]["level"], "N4")

    def test_import_local_merges_cards_and_uses_greatest_on_postgres(self):
        res = auth.upsert_google_user({
            "sub": "sub-2",
            "email": "merge@gmail.com",
            "name": "Merger",
            "picture": "",
        })
        headers = {"Authorization": f"Bearer {res['token']}"}

        # Import cards + bookmark for a card without an existing progress row
        code, _, body, _ = call_api(
            "POST",
            "/api/sync/import-local",
            headers=headers,
            json_data={
                "level": "N3",
                "cards": {
                    "10": {"status": "learning", "repetitions": 2, "intervalDays": 4, "correctCount": 2, "incorrectCount": 0},
                    "invalid_key": {"status": "new"},
                },
                "bookmarks": [99],
            },
        )
        self.assertEqual(code, 200)
        self.assertEqual(body["merged_cards"], 1)

        _, _, prog, _ = call_api("GET", "/api/progress", headers=headers, query="level=N3")
        self.assertIn("10", prog["cards"])
        self.assertIn(99, prog["bookmarks"])

        # Re-importing smaller counts should not downgrade existing counts
        call_api(
            "POST",
            "/api/sync/import-local",
            headers=headers,
            json_data={
                "level": "N3",
                "cards": {
                    "10": {"status": "new", "repetitions": 1, "intervalDays": 1, "correctCount": 1, "incorrectCount": 0},
                },
            },
        )
        _, _, prog2, _ = call_api("GET", "/api/progress", headers=headers, query="level=N3")
        self.assertEqual(prog2["cards"]["10"]["repetitions"], 2)

        # Verify SQL dialect switch emits GREATEST when connection is PostgreSQL wrapper
        executed_sqls = []
        class _DummyCursor:
            def execute(self, sql, params=None):
                executed_sqls.append(sql)
            def executemany(self, sql, seq):
                executed_sqls.append(sql)
        class _DummyPgConn:
            def cursor(self):
                return _DummyCursor()
            def commit(self):
                pass
            def rollback(self):
                pass
            def close(self):
                pass

        from contextlib import contextmanager
        @contextmanager
        def _fake_pg_session():
            conn = _DummyPgConn()
            yield conn, conn.cursor()

        with patch.object(server, "db_session", _fake_pg_session), patch.object(server, "is_pg_conn", return_value=True):
            req = server.ImportLocalRequest(
                level="N3",
                cards={"5": {"status": "learning", "repetitions": 1, "intervalDays": 1, "correctCount": 1, "incorrectCount": 0}},
            )
            server.import_local_progress(req, user_id=res["user"]["id"])

        self.assertTrue(any("GREATEST(" in s for s in executed_sqls))
        self.assertFalse(any("MAX(" in s for s in executed_sqls))

    def test_streak_calculation_and_reset_progress(self):
        res = auth.upsert_google_user({
            "sub": "sub-3",
            "email": "streak@gmail.com",
            "name": "Streaker",
            "picture": "",
        })
        user_id = res["user"]["id"]
        headers = {"Authorization": f"Bearer {res['token']}"}

        # Submit one review on N3 and one on N4
        code, _, rev_body, _ = call_api(
            "POST",
            "/api/progress/review",
            headers=headers,
            json_data={"level": "N3", "kanji_id": 1, "is_correct": True, "mode": "quiz"},
        )
        self.assertEqual(code, 200)
        self.assertEqual(rev_body["currentStreak"], 1)
        self.assertEqual(rev_body["bestStreak"], 1)

        call_api(
            "POST",
            "/api/progress/review",
            headers=headers,
            json_data={"level": "N4", "kanji_id": 2, "is_correct": True, "mode": "flashcard"},
        )

        # Insert historical study_logs in VN local timezone for yesterday and 2 days ago, plus older 5-day streak
        now_vn = datetime.now(server.VN_TZ)
        with database.db_session() as (conn, cursor):
            for offset in (1, 2, 10, 11, 12, 13, 14):
                ts = (now_vn - timedelta(days=offset)).isoformat()
                cursor.execute(
                    """
                    INSERT INTO study_logs (user_id, level, kanji_id, mode, is_correct, interval_before, interval_after, created_at)
                    VALUES (?, 'N3', 1, 'flashcard', 1, 1, 2, ?)
                    """,
                    (user_id, ts),
                )
            conn.commit()

        _, _, stats_body, _ = call_api("GET", "/api/stats/dashboard", headers=headers, query="level=N3")
        self.assertEqual(stats_body["currentStreak"], 3)
        self.assertEqual(stats_body["bestStreak"], 5)

        # Reset N3 progress leaves N4 untouched
        code_reset, _, reset_body, _ = call_api("POST", "/api/progress/reset", headers=headers, json_data={"level": "N3"})
        self.assertEqual(code_reset, 200)
        self.assertEqual(reset_body["status"], "reset")

        _, _, prog_n3, _ = call_api("GET", "/api/progress", headers=headers, query="level=N3")
        _, _, prog_n4, _ = call_api("GET", "/api/progress", headers=headers, query="level=N4")
        self.assertEqual(prog_n3["cards"], {})
        self.assertIn("2", prog_n4["cards"])

    def test_health_sanitized_and_path_traversal_blocked(self):
        code, _, body, _ = call_api("GET", "/api/health")
        self.assertEqual(code, 200)
        self.assertEqual(set(body.keys()), {"status", "engine"})

        # Production without Postgres fails fast with 503
        with patch.dict(os.environ, {"VERCEL": "1"}):
            with patch.object(database, "get_postgres_url", return_value=None):
                with self.assertRaises(database.DatabaseUnavailableError):
                    database.get_db()
                code_err, _, body_err, _ = call_api("GET", "/api/health")
                self.assertEqual(code_err, 503)
                self.assertEqual(body_err["status"], "error")

        # Path traversal attempt on /data/{filename}
        with self.assertRaises(server.HTTPException) as ctx:
            server.serve_data_json("../server.py")
        self.assertEqual(ctx.exception.status_code, 400)

        code_pt, _, _, _ = call_api("GET", "/data/..%2Fserver.py")
        self.assertEqual(code_pt, 400)


if __name__ == "__main__":
    unittest.main()
