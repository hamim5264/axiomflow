import sqlite3
import json
import time
from typing import Optional, Dict, Any, List, Tuple

DB_PATH = "axiomflow.db"


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _connect()
    cur = conn.cursor()

    # API Keys
    cur.execute("""
    CREATE TABLE IF NOT EXISTS api_keys (
        key TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        created_at INTEGER NOT NULL
    )
    """)

    # Event log (optional but helpful for dashboard)
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

    # Lead scoring
    cur.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        user_id TEXT PRIMARY KEY,
        score INTEGER NOT NULL DEFAULT 0,
        tags_json TEXT NOT NULL DEFAULT '[]',
        last_message TEXT,
        updated_at INTEGER NOT NULL
    )
    """)

    # Webhook endpoints
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

    # Retryable webhook queue
    cur.execute("""
    CREATE TABLE IF NOT EXISTS webhook_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        endpoint_id INTEGER NOT NULL,
        payload_json TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',   -- pending|sent|failed
        retry_count INTEGER NOT NULL DEFAULT 0,
        last_error TEXT,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL,
        FOREIGN KEY(endpoint_id) REFERENCES webhook_endpoints(id)
    )
    """)

    # Dead letter queue (after max retries)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS dead_letter_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        endpoint_id INTEGER NOT NULL,
        payload_json TEXT NOT NULL,
        error TEXT NOT NULL,
        failed_at INTEGER NOT NULL,
        FOREIGN KEY(endpoint_id) REFERENCES webhook_endpoints(id)
    )
    """)

    conn.commit()
    conn.close()


# -------------------------
# API key helpers
# -------------------------
def is_valid_api_key(api_key: str) -> bool:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM api_keys WHERE key = ?", (api_key,))
    ok = cur.fetchone() is not None
    conn.close()
    return ok


def insert_api_key(key: str, name: str):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO api_keys(key, name, created_at) VALUES (?, ?, ?)",
        (key, name, int(time.time()))
    )
    conn.commit()
    conn.close()


# -------------------------
# Webhook endpoint helpers
# -------------------------
def insert_endpoint(name: str, url: str, secret: str, is_active: int = 1):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO webhook_endpoints(name, url, secret, is_active, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (name, url, secret, int(is_active), int(time.time()))
    )
    conn.commit()
    conn.close()


def get_active_endpoints_by_name(name: str) -> List[Dict[str, Any]]:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, name, url, secret, is_active
        FROM webhook_endpoints
        WHERE name = ? AND is_active = 1
        """,
        (name,)
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# -------------------------
# Lead helpers
# -------------------------
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
        (user_id, int(score), json.dumps(tags), last_message, int(time.time()))
    )
    conn.commit()
    conn.close()


# -------------------------
# Event log
# -------------------------
def log_event_to_db(event_type: str, actor_id: Optional[str], message: Optional[str], metadata: Dict[str, Any]):
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


# -------------------------
# Webhook queue
# -------------------------
def queue_webhook(endpoint_id: int, payload: Dict[str, Any]) -> int:
    now = int(time.time())
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO webhook_queue(endpoint_id, payload_json, status, retry_count, last_error, created_at, updated_at)
        VALUES (?, ?, 'pending', 0, NULL, ?, ?)
        """,
        (endpoint_id, json.dumps(payload), now, now)
    )
    job_id = cur.lastrowid
    conn.commit()
    conn.close()
    return int(job_id)


def fetch_pending_webhooks(limit: int = 20) -> List[Dict[str, Any]]:
    conn = _connect()
    cur = conn.cursor()
    # Grab pending first, then failed (so retries can be processed)
    cur.execute(
        """
        SELECT q.*, e.url, e.secret
        FROM webhook_queue q
        JOIN webhook_endpoints e ON e.id = q.endpoint_id
        WHERE e.is_active = 1 AND q.status IN ('pending','failed')
        ORDER BY q.created_at ASC
        LIMIT ?
        """,
        (int(limit),)
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_webhook_sent(job_id: int):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "UPDATE webhook_queue SET status='sent', updated_at=? WHERE id=?",
        (int(time.time()), int(job_id))
    )
    conn.commit()
    conn.close()


def mark_webhook_failed(job_id: int, retry_count: int, error: str):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE webhook_queue
        SET status='failed', retry_count=?, last_error=?, updated_at=?
        WHERE id=?
        """,
        (int(retry_count), str(error)[:500], int(time.time()), int(job_id))
    )
    conn.commit()
    conn.close()


def move_to_dead_letter(job_row: Dict[str, Any], error: str):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO dead_letter_queue(endpoint_id, payload_json, error, failed_at)
        VALUES (?, ?, ?, ?)
        """,
        (int(job_row["endpoint_id"]), job_row["payload_json"], str(error)[:1000], int(time.time()))
    )
    # Remove from main queue (so it doesn't loop forever)
    cur.execute("DELETE FROM webhook_queue WHERE id = ?", (int(job_row["id"]),))
    conn.commit()
    conn.close()


def list_dead_letters(limit: int = 50) -> List[Dict[str, Any]]:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT d.id, d.endpoint_id, d.payload_json, d.error, d.failed_at, e.name as endpoint_name, e.url
        FROM dead_letter_queue d
        JOIN webhook_endpoints e ON e.id = d.endpoint_id
        ORDER BY d.failed_at DESC
        LIMIT ?
        """,
        (int(limit),)
    )
    rows = cur.fetchall()
    conn.close()
    out = []
    for r in rows:
        out.append({
            "id": r["id"],
            "endpoint_id": r["endpoint_id"],
            "endpoint_name": r["endpoint_name"],
            "url": r["url"],
            "payload": json.loads(r["payload_json"]),
            "error": r["error"],
            "failed_at": r["failed_at"],
        })
    return out

# =========================
# DASHBOARD QUERIES
# =========================

def get_stats():
    conn = _connect()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM events")
    total_events = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM leads")
    total_leads = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM leads WHERE score >= 10")
    hot_leads = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM webhook_queue WHERE status='sent'")
    webhooks_sent = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM webhook_queue WHERE status='failed'")
    webhooks_failed = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM dead_letter_queue")
    dead_letters = cur.fetchone()[0]

    conn.close()

    return {
        "total_events": total_events,
        "total_leads": total_leads,
        "hot_leads": hot_leads,
        "webhooks_sent": webhooks_sent,
        "webhooks_failed": webhooks_failed,
        "dead_letters": dead_letters,
    }


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
        (int(limit),)
    )
    rows = cur.fetchall()
    conn.close()

    leads = []
    for r in rows:
        score = int(r["score"])
        status = "hot" if score >= 10 else "warm" if score >= 5 else "cold"

        leads.append({
            "user_id": r["user_id"],
            "score": score,
            "tags": json.loads(r["tags_json"] or "[]"),
            "last_message": r["last_message"],
            "status": status,
            "updated_at": r["updated_at"],
        })

    return leads


def list_recent_events(limit: int = 50):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT event_type, actor_id, message, created_at
        FROM events
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (int(limit),)
    )
    rows = cur.fetchall()
    conn.close()

    return [dict(r) for r in rows]


def list_webhook_queue(limit: int = 50):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT q.id, e.name as endpoint, q.status, q.retry_count,
               q.last_error, q.created_at
        FROM webhook_queue q
        JOIN webhook_endpoints e ON e.id = q.endpoint_id
        ORDER BY q.created_at DESC
        LIMIT ?
        """,
        (int(limit),)
    )
    rows = cur.fetchall()
    conn.close()

    return [dict(r) for r in rows]
