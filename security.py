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
# API KEY HELPERS
# =========================
def generate_api_key() -> str:
    return API_KEY_PREFIX + secrets.token_urlsafe(32)


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def key_preview(raw_key: str) -> str:
    if not raw_key:
        return ""
    return f"{raw_key[:10]}…{raw_key[-4:]}"


# =========================
# API KEYS
# =========================
def insert_api_key(raw_key: str, name: str):
    conn = _connect()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO api_keys(key, name, created_at)
        VALUES (?, ?, ?)
        """,
        (hash_api_key(raw_key), name, int(time.time())),
    )

    conn.commit()
    conn.close()


def is_valid_api_key(raw_key: str) -> bool:
    conn = _connect()
    cur = conn.cursor()

    cur.execute(
        "SELECT 1 FROM api_keys WHERE key = ?",
        (hash_api_key(raw_key),),
    )

    ok = cur.fetchone() is not None
    conn.close()
    return ok


def list_api_keys():
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
            "name": r["name"],
            "key_preview": key_preview(r["key"]),
            "created_at": r["created_at"],
            "status": "ACTIVE",
        }
        for r in rows
    ]
