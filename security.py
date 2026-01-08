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
    CREATE TABLE IF NOT EXISTS webhook_endpoints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        url TEXT NOT NULL,
        secret TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at INTEGER NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS webhook_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        endpoint_id INTEGER NOT NULL,
        payload_json TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        retry_count INTEGER NOT NULL DEFAULT 0,
        last_error TEXT,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS dead_letter_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        endpoint_id INTEGER NOT NULL,
        payload_json TEXT NOT NULL,
        error TEXT NOT NULL,
        failed_at INTEGER NOT NULL
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
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def key_preview(raw_key: str) -> str:
    if not raw_key:
        return ""
    return f"{raw_key[:6]}••••••{raw_key[-4:]}"


# =========================
# API KEYS
# =========================
def insert_api_key(key: str, name: str):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO api_keys(key, name, created_at) VALUES (?, ?, ?)",
        (key, name, int(time.time()))
    )
    conn.commit()
    conn.close()


def is_valid_api_key(api_key: str) -> bool:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM api_keys WHERE key = ?", (api_key,))
    ok = cur.fetchone() is not None
    conn.close()
    return ok


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


# =========================
# EVENTS
# =========================
def log_event_to_db(
    event_type: str,
    actor_id: Optional[str],
    message: Optional[str],
    metadata: Dict[str, Any],
):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO events(event_type, actor_id, message, metadata_json, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (event_type, actor_id, message, json.dumps(metadata or {}), int(time.time()))
    )
    conn.commit()
    conn.close()


def list_recent_events(limit: int = 50):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, event_type, actor_id, message, metadata_json, created_at
        FROM events
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,)
    )
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": r["id"],
            "event_type": r["event_type"],
            "actor_id": r["actor_id"],
            "message": r["message"],
            "metadata": json.loads(r["metadata_json"] or "{}"),
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def list_events_by_actor(actor_id: str, limit: int = 200):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, event_type, actor_id, message, metadata_json, created_at
        FROM events
        WHERE actor_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (actor_id, limit)
    )
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": r["id"],
            "event_type": r["event_type"],
            "actor_id": r["actor_id"],
            "message": r["message"],
            "metadata": json.loads(r["metadata_json"] or "{}"),
            "created_at": r["created_at"],
        }
        for r in rows
    ]


# =========================
# LEADS
# =========================
def get_lead(user_id: str) -> Dict[str, Any]:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM leads WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return {"user_id": user_id, "score": 0, "tags": [], "last_message": None}

    return {
        "user_id": row["user_id"],
        "score": int(row["score"]),
        "tags": json.loads(row["tags_json"] or "[]"),
        "last_message": row["last_message"],
    }


def upsert_lead(user_id: str, score: int, tags: List[str], last_message: Optional[str]):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO leads(user_id, score, tags_json, last_message, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            score=excluded.score,
            tags_json=excluded.tags_json,
            last_message=excluded.last_message,
            updated_at=excluded.updated_at
        """,
        (user_id, score, json.dumps(tags), last_message, int(time.time()))
    )
    conn.commit()
    conn.close()


def list_leads(limit: int = 100):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT user_id, score, tags_json, last_message, updated_at
        FROM leads
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (limit,)
    )
    rows = cur.fetchall()
    conn.close()

    out = []
    for r in rows:
        score = int(r["score"])
        status = "hot" if score >= 10 else "warm" if score >= 5 else "cold"
        out.append({
            "actor_id": r["user_id"],
            "status": status,
            "score": score,
            "last_message": r["last_message"],
            "last_seen_at": r["updated_at"],
        })
    return out


# =========================
# DASHBOARD STATS
# =========================
def get_stats():
    conn = _connect()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM events")
    total_events = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM leads")
    total_leads = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM webhook_queue")
    webhook_queue = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM dead_letter_queue")
    dead_letters = cur.fetchone()[0]

    cur.execute("SELECT MAX(created_at) FROM events")
    last_event_at = cur.fetchone()[0]

    conn.close()

    return {
        "total_events": total_events,
        "total_leads": total_leads,
        "webhook_queue": webhook_queue,
        "dead_letters": dead_letters,
        "last_event_at": last_event_at,
    }
