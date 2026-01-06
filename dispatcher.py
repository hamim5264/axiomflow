import json
import time
import hmac
import hashlib
import urllib.request
import urllib.error

from storage import (
    fetch_pending_webhooks,
    mark_webhook_sent,
    mark_webhook_failed,
    move_to_dead_letter,
)

MAX_RETRIES = 3
TIMEOUT_SECONDS = 5


def _sign(secret: str, body_bytes: bytes, timestamp: int) -> str:
    # HMAC over: "{timestamp}.{body}"
    msg = str(timestamp).encode("utf-8") + b"." + body_bytes
    digest = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def dispatch_pending(limit: int = 20) -> dict:
    jobs = fetch_pending_webhooks(limit=limit)
    sent = 0
    failed = 0
    dead = 0

    for job in jobs:
        job_id = job["id"]
        url = job["url"]
        secret = job["secret"]
        retry_count = int(job["retry_count"] or 0)

        payload = json.loads(job["payload_json"])
        body_bytes = json.dumps(payload).encode("utf-8")
        ts = int(time.time())

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AxiomFlow/0.1.0",
            "X-AxiomFlow-Timestamp": str(ts),
            "X-AxiomFlow-Signature": _sign(secret, body_bytes, ts),
        }

        req = urllib.request.Request(url, data=body_bytes, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
                status = resp.getcode()

            # Treat 2xx as success
            if 200 <= status < 300:
                mark_webhook_sent(job_id)
                sent += 1
            else:
                raise RuntimeError(f"Non-2xx status: {status}")

        except Exception as e:
            retry_count += 1

            # reached max retries -> dead letter
            if retry_count >= MAX_RETRIES:
                move_to_dead_letter(job, error=str(e))
                dead += 1
            else:
                mark_webhook_failed(job_id, retry_count=retry_count, error=str(e))
                failed += 1

    return {"processed": len(jobs), "sent": sent, "failed": failed, "dead": dead}
