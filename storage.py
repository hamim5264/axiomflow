# import sqlite3
# import json
# import time
# from typing import Optional, Dict, Any, List

# DB_PATH = "axiomflow.db"


# # =========================
# # DB CONNECTION
# # =========================
# def _connect():
#     conn = sqlite3.connect(DB_PATH)
#     conn.row_factory = sqlite3.Row
#     return conn


# # =========================
# # INIT
# # =========================
# def init_db():
#     conn = _connect()
#     cur = conn.cursor()

#     cur.execute("""
#     CREATE TABLE IF NOT EXISTS api_keys (
#         key TEXT PRIMARY KEY,
#         name TEXT NOT NULL,
#         created_at INTEGER NOT NULL
#     )
#     """)

#     cur.execute("""
#     CREATE TABLE IF NOT EXISTS events (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         event_type TEXT NOT NULL,
#         actor_id TEXT,
#         message TEXT,
#         metadata_json TEXT,
#         created_at INTEGER NOT NULL
#     )
#     """)

#     cur.execute("""
#     CREATE TABLE IF NOT EXISTS leads (
#         user_id TEXT PRIMARY KEY,
#         score INTEGER NOT NULL DEFAULT 0,
#         tags_json TEXT NOT NULL DEFAULT '[]',
#         last_message TEXT,
#         updated_at INTEGER NOT NULL
#     )
#     """)

#     cur.execute("""
#     CREATE TABLE IF NOT EXISTS webhook_endpoints (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         name TEXT NOT NULL,
#         url TEXT NOT NULL,
#         secret TEXT NOT NULL,
#         is_active INTEGER NOT NULL DEFAULT 1,
#         created_at INTEGER NOT NULL
#     )
#     """)

#     cur.execute("""
#     CREATE TABLE IF NOT EXISTS webhook_queue (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         endpoint_id INTEGER NOT NULL,
#         payload_json TEXT NOT NULL,
#         status TEXT NOT NULL DEFAULT 'pending',
#         retry_count INTEGER NOT NULL DEFAULT 0,
#         last_error TEXT,
#         created_at INTEGER NOT NULL,
#         updated_at INTEGER NOT NULL,
#         FOREIGN KEY(endpoint_id) REFERENCES webhook_endpoints(id)
#     )
#     """)

#     cur.execute("""
#     CREATE TABLE IF NOT EXISTS dead_letter_queue (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         endpoint_id INTEGER NOT NULL,
#         payload_json TEXT NOT NULL,
#         error TEXT NOT NULL,
#         failed_at INTEGER NOT NULL,
#         FOREIGN KEY(endpoint_id) REFERENCES webhook_endpoints(id)
#     )
#     """)

#     conn.commit()
#     conn.close()


# # =========================
# # API KEYS
# # =========================
# def is_valid_api_key(api_key: str) -> bool:
#     conn = _connect()
#     cur = conn.cursor()
#     cur.execute("SELECT 1 FROM api_keys WHERE key = ?", (api_key,))
#     ok = cur.fetchone() is not None
#     conn.close()
#     return ok


# def insert_api_key(key: str, name: str):
#     conn = _connect()
#     cur = conn.cursor()
#     cur.execute(
#         "INSERT OR REPLACE INTO api_keys(key, name, created_at) VALUES (?, ?, ?)",
#         (key, name, int(time.time()))
#     )
#     conn.commit()
#     conn.close()


# # =========================
# # WEBHOOK ENDPOINTS
# # =========================
# def insert_endpoint(name: str, url: str, secret: str, is_active: int = 1):
#     conn = _connect()
#     cur = conn.cursor()
#     cur.execute(
#         """
#         INSERT INTO webhook_endpoints(name, url, secret, is_active, created_at)
#         VALUES (?, ?, ?, ?, ?)
#         """,
#         (name, url, secret, int(is_active), int(time.time()))
#     )
#     conn.commit()
#     conn.close()


# def get_active_endpoints_by_name(name: str) -> List[Dict[str, Any]]:
#     conn = _connect()
#     cur = conn.cursor()
#     cur.execute(
#         """
#         SELECT id, name, url, secret
#         FROM webhook_endpoints
#         WHERE name = ? AND is_active = 1
#         """,
#         (name,)
#     )
#     rows = cur.fetchall()
#     conn.close()
#     return [dict(r) for r in rows]


# # =========================
# # LEADS (USED BY RULES)
# # =========================
# def get_lead(user_id: str) -> Dict[str, Any]:
#     conn = _connect()
#     cur = conn.cursor()
#     cur.execute("SELECT * FROM leads WHERE user_id = ?", (user_id,))
#     row = cur.fetchone()
#     conn.close()

#     if not row:
#         return {
#             "user_id": user_id,
#             "score": 0,
#             "tags": [],
#             "last_message": None,
#         }

#     return {
#         "user_id": row["user_id"],
#         "score": int(row["score"]),
#         "tags": json.loads(row["tags_json"] or "[]"),
#         "last_message": row["last_message"],
#     }


# def upsert_lead(
#     user_id: str,
#     score: int,
#     tags: List[str],
#     last_message: Optional[str],
# ):
#     conn = _connect()
#     cur = conn.cursor()
#     cur.execute(
#         """
#         INSERT INTO leads(user_id, score, tags_json, last_message, updated_at)
#         VALUES (?, ?, ?, ?, ?)
#         ON CONFLICT(user_id) DO UPDATE SET
#             score=excluded.score,
#             tags_json=excluded.tags_json,
#             last_message=excluded.last_message,
#             updated_at=excluded.updated_at
#         """,
#         (
#             user_id,
#             int(score),
#             json.dumps(tags),
#             last_message,
#             int(time.time()),
#         ),
#     )
#     conn.commit()
#     conn.close()


# # =========================
# # EVENTS
# # =========================
# def log_event_to_db(
#     event_type: str,
#     actor_id: Optional[str],
#     message: Optional[str],
#     metadata: Dict[str, Any],
# ):
#     conn = _connect()
#     cur = conn.cursor()
#     cur.execute(
#         """
#         INSERT INTO events(event_type, actor_id, message, metadata_json, created_at)
#         VALUES (?, ?, ?, ?, ?)
#         """,
#         (event_type, actor_id, message, json.dumps(metadata or {}), int(time.time()))
#     )
#     conn.commit()
#     conn.close()


# def list_recent_events(limit: int = 50):
#     conn = _connect()
#     cur = conn.cursor()
#     cur.execute(
#         """
#         SELECT id, event_type, actor_id, message, metadata_json, created_at
#         FROM events
#         ORDER BY created_at DESC
#         LIMIT ?
#         """,
#         (limit,)
#     )
#     rows = cur.fetchall()
#     conn.close()

#     return [
#         {
#             "id": r["id"],
#             "event_type": r["event_type"],
#             "actor_id": r["actor_id"],
#             "message": r["message"],
#             "metadata": json.loads(r["metadata_json"] or "{}"),
#             "created_at": r["created_at"],
#         }
#         for r in rows
#     ]


# def list_events_by_actor(actor_id: str, limit: int = 200):
#     conn = _connect()
#     cur = conn.cursor()
#     cur.execute(
#         """
#         SELECT id, event_type, actor_id, message, metadata_json, created_at
#         FROM events
#         WHERE actor_id = ?
#         ORDER BY created_at DESC
#         LIMIT ?
#         """,
#         (actor_id, limit),
#     )
#     rows = cur.fetchall()
#     conn.close()

#     return [
#         {
#             "id": r["id"],
#             "event_type": r["event_type"],
#             "actor_id": r["actor_id"],
#             "message": r["message"],
#             "metadata": json.loads(r["metadata_json"] or "{}"),
#             "created_at": r["created_at"],
#         }
#         for r in rows
#     ]


# # =========================
# # WEBHOOK QUEUE
# # =========================
# def queue_webhook(endpoint_id: int, payload: Dict[str, Any]) -> int:
#     now = int(time.time())
#     conn = _connect()
#     cur = conn.cursor()
#     cur.execute(
#         """
#         INSERT INTO webhook_queue(endpoint_id, payload_json, status, retry_count, created_at, updated_at)
#         VALUES (?, ?, 'pending', 0, ?, ?)
#         """,
#         (endpoint_id, json.dumps(payload), now, now)
#     )
#     job_id = cur.lastrowid
#     conn.commit()
#     conn.close()
#     return int(job_id)


# def fetch_pending_webhooks(limit: int = 20):
#     conn = _connect()
#     cur = conn.cursor()
#     cur.execute(
#         """
#         SELECT q.*, e.url, e.secret
#         FROM webhook_queue q
#         JOIN webhook_endpoints e ON e.id = q.endpoint_id
#         WHERE e.is_active = 1 AND q.status IN ('pending','failed')
#         ORDER BY q.created_at ASC
#         LIMIT ?
#         """,
#         (limit,)
#     )
#     rows = cur.fetchall()
#     conn.close()
#     return [dict(r) for r in rows]


# def mark_webhook_sent(job_id: int):
#     conn = _connect()
#     cur = conn.cursor()
#     cur.execute(
#         "UPDATE webhook_queue SET status='sent', updated_at=? WHERE id=?",
#         (int(time.time()), job_id)
#     )
#     conn.commit()
#     conn.close()


# def mark_webhook_failed(job_id: int, retry_count: int, error: str):
#     conn = _connect()
#     cur = conn.cursor()
#     cur.execute(
#         """
#         UPDATE webhook_queue
#         SET status='failed', retry_count=?, last_error=?, updated_at=?
#         WHERE id=?
#         """,
#         (retry_count, error[:500], int(time.time()), job_id)
#     )
#     conn.commit()
#     conn.close()


# def move_to_dead_letter(job_row: Dict[str, Any], error: str):
#     conn = _connect()
#     cur = conn.cursor()
#     cur.execute(
#         """
#         INSERT INTO dead_letter_queue(endpoint_id, payload_json, error, failed_at)
#         VALUES (?, ?, ?, ?)
#         """,
#         (job_row["endpoint_id"], job_row["payload_json"], error[:1000], int(time.time()))
#     )
#     cur.execute("DELETE FROM webhook_queue WHERE id = ?", (job_row["id"],))
#     conn.commit()
#     conn.close()


# # =========================
# # DASHBOARD
# # =========================
# def list_leads(limit: int = 100):
#     conn = _connect()
#     cur = conn.cursor()
#     cur.execute(
#         """
#         SELECT user_id, score, tags_json, last_message, updated_at
#         FROM leads
#         ORDER BY updated_at DESC
#         LIMIT ?
#         """,
#         (limit,)
#     )
#     rows = cur.fetchall()
#     conn.close()

#     out = []
#     for r in rows:
#         score = int(r["score"])
#         status = "hot" if score >= 10 else "warm" if score >= 5 else "cold"
#         out.append({
#             "actor_id": r["user_id"],
#             "status": status,
#             "score": score,
#             "last_message": r["last_message"],
#             "last_seen_at": r["updated_at"],
#         })
#     return out


# def get_stats():
#     conn = _connect()
#     cur = conn.cursor()

#     cur.execute("SELECT COUNT(*) FROM events")
#     total_events = cur.fetchone()[0]

#     cur.execute("SELECT COUNT(*) FROM leads")
#     total_leads = cur.fetchone()[0]

#     cur.execute("SELECT COUNT(*) FROM webhook_queue")
#     webhook_queue = cur.fetchone()[0]

#     cur.execute("SELECT COUNT(*) FROM dead_letter_queue")
#     dead_letters = cur.fetchone()[0]

#     cur.execute("SELECT MAX(created_at) FROM events")
#     last_event_at = cur.fetchone()[0]

#     conn.close()

#     return {
#         "total_events": total_events,
#         "total_leads": total_leads,
#         "webhook_queue": webhook_queue,
#         "dead_letters": dead_letters,
#         "last_event_at": last_event_at,
#     }


# def list_webhook_queue(limit: int = 50):
#     conn = _connect()
#     cur = conn.cursor()
#     cur.execute(
#         """
#         SELECT id, status, retry_count, last_error, created_at
#         FROM webhook_queue
#         ORDER BY created_at DESC
#         LIMIT ?
#         """,
#         (limit,)
#     )
#     rows = cur.fetchall()
#     conn.close()
#     return [dict(r) for r in rows]


# def list_dead_letters(limit: int = 50):
#     conn = _connect()
#     cur = conn.cursor()
#     cur.execute(
#         """
#         SELECT id, payload_json, error, failed_at
#         FROM dead_letter_queue
#         ORDER BY failed_at DESC
#         LIMIT ?
#         """,
#         (limit,)
#     )
#     rows = cur.fetchall()
#     conn.close()

#     return [
#         {
#             "id": r["id"],
#             "payload": json.loads(r["payload_json"]),
#             "reason": r["error"],
#             "created_at": r["failed_at"],
#         }
#         for r in rows
#     ]

import sqlite3
import json
import time
from typing import Optional, Dict, Any, List

from security import hash_api_key, key_preview

DB_PATH = "axiomflow.db"


# =========================
# DB CONNECTION
# =========================
def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _table_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    rows = cur.fetchall()
    return [r["name"] for r in rows]


# =========================
# INIT + MIGRATION
# =========================
def init_db():
    conn = _connect()
    cur = conn.cursor()

    # ---- API keys (NEW schema) ----
    # We'll migrate from old schema if needed.
    cur.execute("""
    CREATE TABLE IF NOT EXISTS api_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        key_hash TEXT NOT NULL,
        key_preview TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at INTEGER NOT NULL
    )
    """)

    # ---- Events ----
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

    # ---- Leads ----
    cur.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        user_id TEXT PRIMARY KEY,
        score INTEGER NOT NULL DEFAULT 0,
        tags_json TEXT NOT NULL DEFAULT '[]',
        last_message TEXT,
        updated_at INTEGER NOT NULL
    )
    """)

    # ---- Webhook endpoints ----
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

    # ---- Webhook queue ----
    cur.execute("""
    CREATE TABLE IF NOT EXISTS webhook_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        endpoint_id INTEGER NOT NULL,
        payload_json TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        retry_count INTEGER NOT NULL DEFAULT 0,
        last_error TEXT,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL,
        FOREIGN KEY(endpoint_id) REFERENCES webhook_endpoints(id)
    )
    """)

    # ---- Dead letters ----
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

    # ---- MIGRATION: old api_keys schema (key TEXT PRIMARY KEY...) ----
    # If your DB already has old schema, we migrate it safely once.
    # Old schema columns: key, name, created_at
    cols = _table_columns(conn, "api_keys")

    # If it contains "key" column, that's the old schema (or mixed).
    # But our new schema doesn't have "key". So migrate.
    if "key" in cols:
        # Create new table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS api_keys_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            key_hash TEXT NOT NULL,
            key_preview TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at INTEGER NOT NULL
        )
        """)

        # Copy old keys -> hashed keys
        cur.execute("SELECT key, name, created_at FROM api_keys")
        old_rows = cur.fetchall()
        for r in old_rows:
            raw = r["key"]
            nm = r["name"]
            ca = int(r["created_at"]) if r["created_at"] else int(time.time())
            cur.execute(
                """
                INSERT INTO api_keys_new(name, key_hash, key_preview, is_active, created_at)
                VALUES (?, ?, ?, 1, ?)
                """,
                (nm, hash_api_key(raw), key_preview(raw), ca),
            )

        # Replace table
        cur.execute("DROP TABLE api_keys")
        cur.execute("ALTER TABLE api_keys_new RENAME TO api_keys")

        conn.commit()

    conn.close()


# =========================
# API KEYS
# =========================
def is_valid_api_key(api_key: str) -> bool:
    """
    Validate raw api key from header.
    Stored keys are hashed in DB.
    """
    if not api_key:
        return False

    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM api_keys WHERE key_hash = ? AND is_active = 1",
        (hash_api_key(api_key),),
    )
    ok = cur.fetchone() is not None
    conn.close()
    return ok


def insert_api_key(raw_key: str, name: str) -> Dict[str, Any]:
    """
    Save key securely (hash), return stored record details
    """
    now = int(time.time())
    conn = _connect()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO api_keys(name, key_hash, key_preview, is_active, created_at)
        VALUES (?, ?, ?, 1, ?)
        """,
        (name, hash_api_key(raw_key), key_preview(raw_key), now),
    )
    key_id = cur.lastrowid
    conn.commit()
    conn.close()

    return {
        "id": int(key_id),
        "name": name,
        "api_key": raw_key,           # show ONCE in response
        "key_preview": key_preview(raw_key),
        "status": "active",
        "created_at": now,
    }


def list_api_keys(limit: int = 200) -> List[Dict[str, Any]]:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, name, key_preview, is_active, created_at
        FROM api_keys
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (int(limit),),
    )
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": r["id"],
            "name": r["name"],
            "api_key": r["key_preview"],  # masked preview for dashboard table
            "status": "active" if int(r["is_active"]) == 1 else "revoked",
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def revoke_api_key(key_id: int):
    conn = _connect()
    cur = conn.cursor()
    cur.execute("UPDATE api_keys SET is_active = 0 WHERE id = ?", (int(key_id),))
    conn.commit()
    conn.close()


# =========================
# WEBHOOK ENDPOINTS
# =========================
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
        SELECT id, name, url, secret
        FROM webhook_endpoints
        WHERE name = ? AND is_active = 1
        """,
        (name,),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# =========================
# LEADS (USED BY RULES)
# =========================
def get_lead(user_id: str) -> Dict[str, Any]:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM leads WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return {
            "user_id": user_id,
            "score": 0,
            "tags": [],
            "last_message": None,
        }

    return {
        "user_id": row["user_id"],
        "score": int(row["score"]),
        "tags": json.loads(row["tags_json"] or "[]"),
        "last_message": row["last_message"],
    }


def upsert_lead(
    user_id: str,
    score: int,
    tags: List[str],
    last_message: Optional[str],
):
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
        (
            user_id,
            int(score),
            json.dumps(tags),
            last_message,
            int(time.time()),
        ),
    )
    conn.commit()
    conn.close()


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
        (int(limit),)
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
        (actor_id, int(limit)),
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
# WEBHOOK QUEUE
# =========================
def queue_webhook(endpoint_id: int, payload: Dict[str, Any]) -> int:
    now = int(time.time())
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO webhook_queue(endpoint_id, payload_json, status, retry_count, created_at, updated_at)
        VALUES (?, ?, 'pending', 0, ?, ?)
        """,
        (int(endpoint_id), json.dumps(payload), now, now)
    )
    job_id = cur.lastrowid
    conn.commit()
    conn.close()
    return int(job_id)


def fetch_pending_webhooks(limit: int = 20):
    conn = _connect()
    cur = conn.cursor()
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
    cur.execute("DELETE FROM webhook_queue WHERE id = ?", (int(job_row["id"]),))
    conn.commit()
    conn.close()


# =========================
# DASHBOARD
# =========================
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


def list_webhook_queue(limit: int = 50):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT q.id, e.name as source, e.url as url, q.status, q.retry_count as attempts,
               q.last_error, q.created_at, q.payload_json
        FROM webhook_queue q
        JOIN webhook_endpoints e ON e.id = q.endpoint_id
        ORDER BY q.created_at DESC
        LIMIT ?
        """,
        (int(limit),)
    )
    rows = cur.fetchall()
    conn.close()

    # match your frontend expected fields
    out = []
    for r in rows:
        out.append({
            "id": r["id"],
            "source": r["source"],
            "url": r["url"],
            "status": r["status"],
            "attempts": r["attempts"],
            "next_attempt_at": None,  # optional (frontend can show "-")
            "last_error": r["last_error"],
            "created_at": r["created_at"],
            "payload": json.loads(r["payload_json"] or "{}"),
        })
    return out


def list_dead_letters(limit: int = 50):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, payload_json, error, failed_at
        FROM dead_letter_queue
        ORDER BY failed_at DESC
        LIMIT ?
        """,
        (int(limit),)
    )
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": r["id"],
            "payload": json.loads(r["payload_json"] or "{}"),
            "reason": r["error"],
            "created_at": r["failed_at"],
        }
        for r in rows
    ]
