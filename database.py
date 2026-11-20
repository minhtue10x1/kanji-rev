# -*- coding: utf-8 -*-
"""
Database configuration and multi-engine adapter for Kanji Master.
Supports:
1. PostgreSQL / Vercel Postgres / Neon (when POSTGRES_URL or DATABASE_URL is set)
2. SQLite (local development only: kanji_users.db or KANJI_DB_PATH)
"""

import os
import ssl
import sqlite3
import urllib.parse
from contextlib import contextmanager
from typing import List, Optional

# Drivers
try:
    import psycopg2
    from psycopg2 import pool as pg_pool
    from psycopg2.extras import RealDictCursor
    HAS_PSYCOPG2 = True
except Exception:
    pg_pool = None
    HAS_PSYCOPG2 = False

try:
    import pg8000.dbapi
    HAS_PG8000 = True
except Exception:
    HAS_PG8000 = False


class DatabaseUnavailableError(RuntimeError):
    """Raised when the configured database cannot be reached."""


_PG_POOL = None
_PG_POOL_URL = None
_SCHEMA_INITIALIZED = False


def get_default_db_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "kanji_users.db")


def get_postgres_url() -> Optional[str]:
    """Resolve PostgreSQL connection URL, preferring pooled endpoints."""
    if os.environ.get("POSTGRES_URL"):
        return os.environ.get("POSTGRES_URL")
    if os.environ.get("DATABASE_URL"):
        return os.environ.get("DATABASE_URL")

    # Pass 1: Prefer pooled connection strings from Vercel Storage / Neon custom prefixes
    skip_markers = ("UNPOOLED", "NON_POOLING", "NO_SSL", "PRISMA")
    for k, v in os.environ.items():
        if (k.endswith("_POSTGRES_URL") or k.endswith("_DATABASE_URL")) and not any(m in k for m in skip_markers):
            if v and (v.startswith("postgres://") or v.startswith("postgresql://")):
                return v

    # Pass 2: Fall back to any prefixed Postgres URL if no pooled URL was provided
    for k, v in os.environ.items():
        if k.endswith("_POSTGRES_URL") or k.endswith("_DATABASE_URL"):
            if v and (v.startswith("postgres://") or v.startswith("postgresql://")):
                return v
    return None


class DictRow(dict):
    """Row wrapper allowing both dictionary key access and index access."""

    def __init__(self, data: dict, values: list = None):
        super().__init__(data)
        self._values = values if values is not None else list(data.values())

    def __getitem__(self, item):
        if isinstance(item, int):
            return self._values[item]
        return super().__getitem__(item)


class PostgresCursorWrapper:
    def __init__(self, cursor):
        self.cursor = cursor

    def execute(self, sql: str, params=None):
        clean_sql = sql.replace("?", "%s")
        if params is not None:
            if isinstance(params, list):
                params = tuple(params)
            return self.cursor.execute(clean_sql, params)
        return self.cursor.execute(clean_sql)

    def executemany(self, sql: str, seq_of_params):
        clean_sql = sql.replace("?", "%s")
        return self.cursor.executemany(clean_sql, seq_of_params)

    def fetchone(self) -> Optional[DictRow]:
        row = self.cursor.fetchone()
        if not row:
            return None
        if isinstance(row, dict):
            return DictRow(row)
        if self.cursor.description:
            cols = [d[0] for d in self.cursor.description]
            return DictRow(dict(zip(cols, row)), list(row))
        return row

    def fetchall(self) -> List[DictRow]:
        rows = self.cursor.fetchall()
        if not rows:
            return []
        if isinstance(rows[0], dict):
            return [DictRow(r) for r in rows]
        if self.cursor.description:
            cols = [d[0] for d in self.cursor.description]
            return [DictRow(dict(zip(cols, r)), list(r)) for r in rows]
        return rows


class PostgresConnectionWrapper:
    def __init__(self, conn, pool=None):
        self.conn = conn
        self._pool = pool
        self._closed = False

    def cursor(self):
        return PostgresCursorWrapper(self.conn.cursor())

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._pool is not None:
            try:
                is_broken = bool(getattr(self.conn, "closed", 0))
                self._pool.putconn(self.conn, close=is_broken)
                return
            except Exception:
                pass
        try:
            self.conn.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            try:
                self.rollback()
            except Exception:
                pass
        self.close()
        return False


def _get_pg_pool(pg_url: str):
    global _PG_POOL, _PG_POOL_URL
    if _PG_POOL is None or _PG_POOL_URL != pg_url or getattr(_PG_POOL, "closed", False):
        if _PG_POOL is not None and not getattr(_PG_POOL, "closed", False):
            try:
                _PG_POOL.closeall()
            except Exception:
                pass
        _PG_POOL = pg_pool.SimpleConnectionPool(
            minconn=1,
            maxconn=5,
            dsn=pg_url,
            cursor_factory=RealDictCursor,
        )
        _PG_POOL_URL = pg_url
    return _PG_POOL


def _reset_pg_pool():
    global _PG_POOL, _PG_POOL_URL
    if _PG_POOL is not None:
        try:
            _PG_POOL.closeall()
        except Exception:
            pass
    _PG_POOL = None
    _PG_POOL_URL = None


def get_db():
    """
    Returns an active database connection.
    Connects to PostgreSQL when POSTGRES_URL/DATABASE_URL is configured; fails fast on production if unavailable.
    Uses local SQLite only in local development when no Postgres URL is set.
    """
    pg_url = get_postgres_url()
    if pg_url:
        if pg_url.startswith("postgres://"):
            pg_url = pg_url.replace("postgres://", "postgresql://", 1)

        if HAS_PSYCOPG2:
            try:
                pool = _get_pg_pool(pg_url)
                conn = pool.getconn()
                # Guard against stale idle serverless connections
                if getattr(conn, "closed", 0):
                    pool.putconn(conn, close=True)
                    conn = pool.getconn()
                return PostgresConnectionWrapper(conn, pool=pool)
            except Exception as e:
                print(f"psycopg2 pooled connection warning, falling back to pg8000: {e}")
                _reset_pg_pool()

        if HAS_PG8000:
            try:
                parsed = urllib.parse.urlparse(pg_url)
                user = urllib.parse.unquote(parsed.username) if parsed.username else None
                password = urllib.parse.unquote(parsed.password) if parsed.password else None
                db_name = parsed.path.lstrip("/").split("?")[0]
                ssl_ctx = ssl.create_default_context()
                conn = pg8000.dbapi.connect(
                    user=user,
                    password=password,
                    host=parsed.hostname,
                    port=parsed.port or 5432,
                    database=db_name,
                    ssl_context=ssl_ctx,
                )
                return PostgresConnectionWrapper(conn)
            except Exception as e:
                print(f"pg8000 connection error: {e}")

        raise DatabaseUnavailableError("PostgreSQL connection failed")

    if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        raise DatabaseUnavailableError("Database not configured in production")

    target_path = os.environ.get("KANJI_DB_PATH") or get_default_db_path()
    try:
        conn = sqlite3.connect(target_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode = WAL;")
        except Exception:
            pass
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn
    except Exception as e:
        raise DatabaseUnavailableError(f"SQLite connection failed at {target_path}: {e}")


def is_pg_conn(conn) -> bool:
    return isinstance(conn, PostgresConnectionWrapper)


def is_postgres() -> bool:
    return bool(get_postgres_url())


@contextmanager
def db_session():
    """Context manager guaranteeing transaction rollback on error and connection close."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        yield conn, cursor
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()


def init_database(force: bool = False):
    """Initializes multi-level schema tables and indexes on SQLite or PostgreSQL."""
    global _SCHEMA_INITIALIZED
    if _SCHEMA_INITIALIZED and not force:
        return

    with db_session() as (conn, cursor):
        if is_pg_conn(conn):
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                name TEXT,
                avatar_url TEXT,
                google_sub TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                last_login_at TEXT NOT NULL
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                current_level TEXT DEFAULT 'N3',
                theme TEXT DEFAULT 'light',
                shuffle_queue INTEGER DEFAULT 0,
                daily_goal INTEGER DEFAULT 20,
                show_furigana INTEGER DEFAULT 1,
                auto_audio INTEGER DEFAULT 0,
                updated_at TEXT NOT NULL
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_kanji_progress (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                level TEXT NOT NULL DEFAULT 'N3',
                kanji_id INTEGER NOT NULL,
                status TEXT DEFAULT 'new',
                repetitions INTEGER DEFAULT 0,
                interval_days INTEGER DEFAULT 1,
                ease_factor REAL DEFAULT 2.5,
                correct_count INTEGER DEFAULT 0,
                incorrect_count INTEGER DEFAULT 0,
                is_bookmarked INTEGER DEFAULT 0,
                last_reviewed_at TEXT,
                next_review_at TEXT,
                UNIQUE(user_id, level, kanji_id)
            );
            """)

            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_progress_user_lvl_due
            ON user_kanji_progress (user_id, level, next_review_at, status);
            """)
            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_progress_user_lvl_bm
            ON user_kanji_progress (user_id, level, is_bookmarked);
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS study_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                level TEXT NOT NULL DEFAULT 'N3',
                mode TEXT NOT NULL,
                filter_type TEXT NOT NULL,
                chapter_num INTEGER,
                queue_json TEXT NOT NULL,
                current_index INTEGER DEFAULT 0,
                completed_count INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                updated_at TEXT NOT NULL
            );
            """)

            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_user_lvl_active
            ON study_sessions (user_id, level, is_active, updated_at);
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS study_logs (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                level TEXT NOT NULL DEFAULT 'N3',
                kanji_id INTEGER NOT NULL,
                session_id TEXT,
                mode TEXT NOT NULL,
                is_correct INTEGER NOT NULL,
                interval_before INTEGER,
                interval_after INTEGER,
                created_at TEXT NOT NULL
            );
            """)

            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_user_lvl_date
            ON study_logs (user_id, level, created_at);
            """)
            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_user_date
            ON study_logs (user_id, created_at);
            """)

            conn.commit()
            _SCHEMA_INITIALIZED = True
            return

        # SQLite Schema (local development / tests)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            avatar_url TEXT,
            google_sub TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL,
            last_login_at TEXT NOT NULL
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id TEXT PRIMARY KEY,
            current_level TEXT DEFAULT 'N3',
            theme TEXT DEFAULT 'light',
            shuffle_queue INTEGER DEFAULT 0,
            daily_goal INTEGER DEFAULT 20,
            show_furigana INTEGER DEFAULT 1,
            auto_audio INTEGER DEFAULT 0,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_kanji_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            level TEXT NOT NULL DEFAULT 'N3',
            kanji_id INTEGER NOT NULL,
            status TEXT DEFAULT 'new',
            repetitions INTEGER DEFAULT 0,
            interval_days INTEGER DEFAULT 1,
            ease_factor REAL DEFAULT 2.5,
            correct_count INTEGER DEFAULT 0,
            incorrect_count INTEGER DEFAULT 0,
            is_bookmarked INTEGER DEFAULT 0,
            last_reviewed_at TEXT,
            next_review_at TEXT,
            UNIQUE(user_id, level, kanji_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_progress_user_lvl_due
        ON user_kanji_progress (user_id, level, next_review_at, status);
        """)
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_progress_user_lvl_bm
        ON user_kanji_progress (user_id, level, is_bookmarked);
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS study_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            level TEXT NOT NULL DEFAULT 'N3',
            mode TEXT NOT NULL,
            filter_type TEXT NOT NULL,
            chapter_num INTEGER,
            queue_json TEXT NOT NULL,
            current_index INTEGER DEFAULT 0,
            completed_count INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_user_lvl_active
        ON study_sessions (user_id, level, is_active, updated_at);
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS study_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            level TEXT NOT NULL DEFAULT 'N3',
            kanji_id INTEGER NOT NULL,
            session_id TEXT,
            mode TEXT NOT NULL,
            is_correct INTEGER NOT NULL,
            interval_before INTEGER,
            interval_after INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_logs_user_lvl_date
        ON study_logs (user_id, level, created_at);
        """)
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_logs_user_date
        ON study_logs (user_id, created_at);
        """)

        conn.commit()
        _SCHEMA_INITIALIZED = True


if __name__ == "__main__":
    init_database(force=True)
