from typing import List, Dict, Any
from storage import get_lead, upsert_lead, get_active_endpoints_by_name, queue_webhook


def evaluate_rules(event) -> List[str]:
    """
    Returns actions list for debugging / dashboard logs.
    """
    actions: List[str] = []

    user_id = event.actor_id or "anonymous"
    msg = (event.message or "").lower()

    lead = get_lead(user_id)
    score = int(lead["score"])
    tags = list(lead["tags"])

    # --- simple scoring rules ---
    if "price" in msg or "pricing" in msg:
        score += 5
        if "pricing_interest" not in tags:
            tags.append("pricing_interest")
        actions.append("tag:pricing_interest")

    if "demo" in msg:
        score += 7
        if "demo_request" not in tags:
            tags.append("demo_request")
        actions.append("tag:demo_request")

    # auto reply simulation
    if "price" in msg or "pricing" in msg:
        actions.append("reply:queued")

    # admin alert simulation
    if score >= 10:
        actions.append("admin_alert:queued")

    # save lead state
    upsert_lead(user_id=user_id, score=score, tags=tags, last_message=event.message)

    # --- webhook queueing (NEW) ---
    # Send webhook for hot leads
    if score >= 10:
        endpoints = get_active_endpoints_by_name("default")
        payload = {
            "event": "hot_lead",
            "user_id": user_id,
            "score": score,
            "tags": tags,
            "message": event.message,
        }

        for ep in endpoints:
            job_id = queue_webhook(endpoint_id=ep["id"], payload=payload)
            actions.append(f"webhook:queued:{ep['name']}:{job_id}")

    return actions
