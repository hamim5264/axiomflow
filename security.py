import sqlite3
import json
import time
import secrets
import hashlib
from typing import Dict, Any, List

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

    conn.commit()
    conn.close()


# =========================
# API KEY HELPERS
# =========================
def generate_api_key() -> str:
    return API_KEY_PREFIX + secrets.token_urlsafe(32)


def hash_api_key(raw_key: str) -> str:
    """Used internally if you later want hashed storage"""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def key_preview(raw_key: str) -> str:
    """Safe preview for UI/logs"""
    if not raw_key:
        return ""
    return f"{raw_key[:10]}…{raw_key[-4:]}"


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
        "SELECT key, name, created_at FROM api_keys ORDER BY created_at DESC"
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
