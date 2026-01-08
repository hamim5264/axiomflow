import sqlite3
import json
import time
import secrets
import hashlib
from typing import Optional, Dict, Any, List

DB_PATH = "axiomflow.db"
API_KEY_PREFIX = "axf_"


# =========================
# DB CONNECTION
# =========================
def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# =========================
# INIT
# =========================
def init_db():
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS api_keys (
        key TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        created_at INTEGER NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT NOT NULL,
        actor_id TEXT,
        message TEXT,
        metadata_json TEXT,
        created_at INTEGER NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        user_id TEXT PRIMARY KEY,
        score INTEGER NOT NULL DEFAULT 0,
        tags_json TEXT NOT NULL DEFAULT '[]',
        last_message TEXT,
        updated_at INTEGER NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS webhook_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        payload_json TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at INTEGER NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS dead_letter_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        payload_json TEXT NOT NULL,
        error TEXT NOT NULL,
        failed_at INTEGER NOT NULL
    )
    """)

    conn.commit()
    conn.close()


# =========================
# API KEY UTILITIES
# =========================
def generate_api_key() -> str:
    return API_KEY_PREFIX + secrets.token_urlsafe(32)


def is_valid_api_key(api_key: str) -> bool:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM api_keys WHERE key = ?", (api_key,))
    ok = cur.fetchone() is not None
    conn.close()
    return ok


def has_any_api_key() -> bool:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM api_keys")
    count = cur.fetchone()[0]
    conn.close()
    return count > 0


def insert_api_key(key: str, name: str):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO api_keys(key, name, created_at) VALUES (?, ?, ?)",
        (key, name, int(time.time()))
    )
    conn.commit()
    conn.close()


def list_api_keys() -> List[Dict[str, Any]]:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT key, name, created_at
        FROM api_keys
        ORDER BY created_at DESC
        """
    )
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "key": r["key"],
            "name": r["name"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]
