import json
import httpx
from typing import Any, Dict, List, Optional

from storage import (
    enqueue_webhook_delivery,
    fetch_due_deliveries,
    mark_delivery_sent,
    mark_delivery_failed,
    log_execution,
)


def apply_actions(actor_id: Optional[str], actions: List[Dict[str, Any]]) -> List[str]:
    """
    Apply actions returned by the rules engine.
    Returns a list of "what we did" strings for API response.
    """
    results: List[str] = []

    for a in actions:
        action_type = a.get("type")

        if action_type == "tag":
            # tagging already done inside rules.py (so just log)
            tag = a.get("tag")
            results.append(f"tag:{tag}")
            log_execution(actor_id, f"[AUTO-TAG] tag={tag}")

        elif action_type == "reply":
            msg = a.get("message", "")
            results.append("reply:queued")
            log_execution(actor_id, f"[AUTO-REPLY] {msg}")

        elif action_type == "admin_alert":
            msg = a.get("message", "")
            results.append("admin_alert:queued")
            log_execution(actor_id, f"[ADMIN ALERT] {msg}")

        elif action_type == "webhook":
            endpoint = a.get("endpoint", "default")
            payload = a.get("payload", {})
            delivery_id = enqueue_webhook_delivery(endpoint, payload)
            results.append(f"webhook:queued:{endpoint}:{delivery_id}")
            log_execution(actor_id, f"[WEBHOOK QUEUED] endpoint={endpoint} delivery_id={delivery_id}")

        else:
            # unknown action
            results.append(f"unknown:{action_type}")
            log_execution(actor_id, f"[UNKNOWN ACTION] {json.dumps(a)}")

    return results


def deliver_pending_once(max_items: int = 25) -> Dict[str, Any]:
    """
    Tries to deliver pending outgoing webhooks once.
    Safe to call frequently (e.g., after each /events call).
    """
    due = fetch_due_deliveries(limit=max_items)
    sent = 0
    failed = 0

    for d in due:
        delivery_id = int(d["delivery_id"])
        url = d["endpoint_url"]
        secret = d.get("endpoint_secret") or ""
        payload = json.loads(d["payload_json"])
        attempts = int(d["attempts"]) + 1  # this try

        headers = {"Content-Type": "application/json"}
        # Optional shared-secret header for client verification
        if secret:
            headers["X-AxiomFlow-Secret"] = secret

        try:
            with httpx.Client(timeout=8.0) as client:
                r = client.post(url, json=payload, headers=headers)
                if 200 <= r.status_code < 300:
                    mark_delivery_sent(delivery_id)
                    sent += 1
                    log_execution(None, f"[WEBHOOK SENT] delivery_id={delivery_id} url={url} status={r.status_code}")
                else:
                    err = f"HTTP {r.status_code}: {r.text[:200]}"
                    mark_delivery_failed(delivery_id, err, attempts)
                    failed += 1
                    log_execution(None, f"[WEBHOOK RETRY] delivery_id={delivery_id} url={url} err={err}")
        except Exception as e:
            err = str(e)
            mark_delivery_failed(delivery_id, err, attempts)
            failed += 1
            log_execution(None, f"[WEBHOOK EXCEPTION] delivery_id={delivery_id} url={url} err={err}")

    return {"attempted": len(due), "sent": sent, "failed": failed}
