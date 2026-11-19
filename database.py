# -*- coding: utf-8 -*-
"""
Database configuration and multi-engine adapter for Kanji Master.
Supports:
1. PostgreSQL / Vercel Postgres / Neon (when POSTGRES_URL or DATABASE_URL is set)
2. SQLite (local development: kanji_users.db; serverless fallback: /tmp/kanji_users.db)
"""

import os
import sqlite3
import urllib.parse
from typing import Any, List, Optional, Union, Dict

# Drivers
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_PSYCOPG2 = True
except Exception:
    HAS_PSYCOPG2 = False

try:
    import pg8000.dbapi
    HAS_PG8000 = True
except Exception:
    HAS_PG8000 = False

def get_default_db_path() -> str:
    # On serverless platforms (Vercel, AWS Lambda), the root filesystem is read-only
    # Only /tmp is writable for temporary SQLite storage
    if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        return "/tmp/kanji_users.db"
    return os.path.join(os.path.dirname(__file__), "kanji_users.db")

def get_postgres_url() -> Optional[str]:
    return os.environ.get("POSTGRES_URL") or os.environ.get("DATABASE_URL")

POSTGRES_URL = get_postgres_url()
DB_FILE = os.environ.get("KANJI_DB_PATH", get_default_db_path())


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
        clean_sql = sql.replace('?', '%s')
        if params is not None:
            if isinstance(params, list):
                params = tuple(params)
            return self.cursor.execute(clean_sql, params)
        return self.cursor.execute(clean_sql)

    def executemany(self, sql: str, seq_of_params):
        clean_sql = sql.replace('?', '%s')
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
    def __init__(self, conn):
        self.conn = conn

    def cursor(self):
        return PostgresCursorWrapper(self.conn.cursor())

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()


def get_db():
    """
    Returns an active database connection.
    Connects to PostgreSQL if POSTGRES_URL or DATABASE_URL is defined,
    otherwise connects to SQLite safely.
    """
    pg_url = get_postgres_url()
    if pg_url:
        # Normalize protocol for psycopg2
        if pg_url.startswith("postgres://"):
            pg_url = pg_url.replace("postgres://", "postgresql://", 1)

        if HAS_PSYCOPG2:
            try:
                conn = psycopg2.connect(pg_url, cursor_factory=RealDictCursor)
                return PostgresConnectionWrapper(conn)
            except Exception as e:
                print(f"psycopg2 connection warning, falling back to pg8000: {e}")

        if HAS_PG8000:
            try:
                import ssl
                parsed = urllib.parse.urlparse(pg_url)
                user = urllib.parse.unquote(parsed.username) if parsed.username else None
                password = urllib.parse.unquote(parsed.password) if parsed.password else None
                ssl_ctx = ssl.create_default_context()
                conn = pg8000.dbapi.connect(
                    user=user,
                    password=password,
                    host=parsed.hostname,
                    port=parsed.port or 5432,
                    database=parsed.path.lstrip('/'),
                    ssl_context=ssl_ctx
                )
                return PostgresConnectionWrapper(conn)
            except Exception as e:
                print(f"pg8000 connection warning: {e}")

        print("Warning: PostgreSQL URL present but drivers failed to connect. Falling back to local/tmp SQLite.")

    # SQLite Connection with writable location guarantee
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
        print(f"Warning: SQLite failed at {target_path} ({e}), falling back to in-memory SQLite.")
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn


def is_postgres() -> bool:
    return bool(get_postgres_url())


def init_database():
    """Initializes multi-level schema tables and indexes on SQLite or PostgreSQL."""
    try:
        conn = get_db()
        cursor = conn.cursor()

        if is_postgres():
            print("Initializing schema on PostgreSQL / Vercel Postgres...")
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

            conn.commit()
            conn.close()
            print("PostgreSQL schema & indexes initialized successfully.")
            return

        # SQLite Schema
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

        conn.commit()
        conn.close()
        print("Multi-level SQLite schema & indexes initialized successfully.")
    except Exception as e:
        print(f"init_database safe exception: {e}")

if __name__ == "__main__":
    init_database()
