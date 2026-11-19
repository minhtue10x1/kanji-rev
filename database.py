# -*- coding: utf-8 -*-
"""
Database configuration and multi-engine adapter for Kanji Master.
Seamlessly supports:
1. PostgreSQL / Vercel Postgres / Neon (when POSTGRES_URL or DATABASE_URL is set)
2. SQLite (local development fallback: kanji_users.db)
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
except ImportError:
    HAS_PSYCOPG2 = False

try:
    import pg8000.native
    HAS_PG8000 = True
except ImportError:
    HAS_PG8000 = False

POSTGRES_URL = os.environ.get("POSTGRES_URL") or os.environ.get("DATABASE_URL")
DB_FILE = os.environ.get("KANJI_DB_PATH", os.path.join(os.path.dirname(__file__), "kanji_users.db"))


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
        # Convert SQLite ? placeholders to Postgres %s
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
    otherwise falls back to local SQLite with WAL mode.
    """
    if POSTGRES_URL:
        # PostgreSQL Connection
        pg_url = POSTGRES_URL
        # Normalize protocol for psycopg2 if postgresql:// is needed
        if pg_url.startswith("postgres://"):
            pg_url = pg_url.replace("postgres://", "postgresql://", 1)

        if HAS_PSYCOPG2:
            conn = psycopg2.connect(pg_url, cursor_factory=RealDictCursor)
            return PostgresConnectionWrapper(conn)
        elif HAS_PG8000:
            parsed = urllib.parse.urlparse(pg_url)
            conn = pg8000.native.Connection(
                user=parsed.username,
                password=parsed.password,
                host=parsed.hostname,
                port=parsed.port or 5432,
                database=parsed.path.lstrip('/'),
                ssl_context=True
            )
            return PostgresConnectionWrapper(conn)
        else:
            raise RuntimeError("PostgreSQL URL is set but neither psycopg2 nor pg8000 is installed.")

    # SQLite Connection
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def is_postgres() -> bool:
    return bool(POSTGRES_URL)


def init_database():
    """Initializes multi-level schema tables and indexes on SQLite or PostgreSQL."""
    conn = get_db()
    cursor = conn.cursor()

    if is_postgres():
        print("Initializing schema on PostgreSQL / Vercel Postgres...")
        # PostgreSQL Schema
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

    # Indexes
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

if __name__ == "__main__":
    init_database()
