# from fastapi import FastAPI, Header, HTTPException, BackgroundTasks
# from models import Event
# from rules import evaluate_rules
# from storage import init_db, is_valid_api_key, log_event_to_db, list_dead_letters
# from dispatcher import dispatch_pending

# app = FastAPI(title="AxiomFlow", version="0.1.0")


# @app.on_event("startup")
# def on_startup():
#     init_db()


# def _require_key(x_api_key: str | None):
#     if not x_api_key or not is_valid_api_key(x_api_key):
#         raise HTTPException(status_code=401, detail="Invalid API key")


# @app.post("/events")
# def receive_event(
#     event: Event,
#     background_tasks: BackgroundTasks,
#     x_api_key: str | None = Header(default=None, alias="x-api-key"),
# ):
#     _require_key(x_api_key)

#     # Log event to DB for dashboard later
#     log_event_to_db(event.event_type, event.actor_id, event.message, event.metadata or {})

#     actions = evaluate_rules(event)

#     # Kick dispatcher in background so webhook sends automatically
#     background_tasks.add_task(dispatch_pending, 20)

#     return {"status": "processed", "actions_executed": actions}


# # Manual trigger: useful while testing
# @app.post("/admin/dispatch")
# def admin_dispatch(
#     background_tasks: BackgroundTasks,
#     x_api_key: str | None = Header(default=None, alias="x-api-key"),
# ):
#     _require_key(x_api_key)
#     background_tasks.add_task(dispatch_pending, 50)
#     return {"status": "dispatch_scheduled"}


# # Dead letters: dashboard will use this
# @app.get("/admin/dead-letters")
# def admin_dead_letters(
#     limit: int = 50,
#     x_api_key: str | None = Header(default=None, alias="x-api-key"),
# ):
#     _require_key(x_api_key)
#     return {"items": list_dead_letters(limit=limit)}


# from storage import (
#     get_stats,
#     list_leads,
#     list_recent_events,
#     list_webhook_queue,
# )

# # =========================
# # DASHBOARD APIs
# # =========================

# @app.get("/admin/stats")
# def admin_stats(x_api_key: str | None = Header(default=None, alias="x-api-key")):
#     _require_key(x_api_key)
#     return get_stats()


# @app.get("/admin/leads")
# def admin_leads(
#     limit: int = 100,
#     x_api_key: str | None = Header(default=None, alias="x-api-key"),
# ):
#     _require_key(x_api_key)
#     return {"items": list_leads(limit)}


# @app.get("/admin/recent-events")
# def admin_recent_events(
#     limit: int = 50,
#     x_api_key: str | None = Header(default=None, alias="x-api-key"),
# ):
#     _require_key(x_api_key)
#     return {"items": list_recent_events(limit)}


# @app.get("/admin/webhook-queue")
# def admin_webhook_queue(
#     limit: int = 50,
#     x_api_key: str | None = Header(default=None, alias="x-api-key"),
# ):
#     _require_key(x_api_key)
#     return {"items": list_webhook_queue(limit)}

from fastapi import FastAPI, Header, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from models import Event
from rules import evaluate_rules
from storage import (
    init_db,
    is_valid_api_key,
    log_event_to_db,
    list_dead_letters,
    get_stats,
    list_leads,
    list_recent_events,
    list_webhook_queue,
)
from dispatcher import dispatch_pending

app = FastAPI(title="AxiomFlow", version="0.1.0")
# 🔥 CORS (REQUIRED FOR DASHBOARD)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# STARTUP
# =========================
@app.on_event("startup")
def on_startup():
    init_db()


# =========================
# HEALTH CHECK (IMPORTANT FOR RENDER)
# =========================
@app.get("/")
def health():
    return {"status": "ok", "service": "AxiomFlow"}


# =========================
# AUTH
# =========================
def _require_key(x_api_key: str | None):
    if not x_api_key or not is_valid_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")


# =========================
# CORE EVENT INGESTION
# =========================
@app.post("/events")
def receive_event(
    event: Event,
    background_tasks: BackgroundTasks,
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
):
    _require_key(x_api_key)

    # Log event for dashboard
    log_event_to_db(
        event.event_type,
        event.actor_id,
        event.message,
        event.metadata or {},
    )

    actions = evaluate_rules(event)

    # Async webhook dispatch
    background_tasks.add_task(dispatch_pending, 20)

    return {
        "status": "processed",
        "actions_executed": actions,
    }


# =========================
# ADMIN / OPS
# =========================
@app.post("/admin/dispatch")
def admin_dispatch(
    background_tasks: BackgroundTasks,
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
):
    _require_key(x_api_key)
    background_tasks.add_task(dispatch_pending, 50)
    return {"status": "dispatch_scheduled"}


@app.get("/admin/dead-letters")
def admin_dead_letters(
    limit: int = 50,
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
):
    _require_key(x_api_key)
    return {"items": list_dead_letters(limit)}


# =========================
# DASHBOARD APIs
# =========================
@app.get("/admin/stats")
def admin_stats(x_api_key: str | None = Header(default=None, alias="x-api-key")):
    _require_key(x_api_key)
    return get_stats()


@app.get("/admin/leads")
def admin_leads(
    limit: int = 100,
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
):
    _require_key(x_api_key)
    return {"items": list_leads(limit)}


@app.get("/admin/recent-events")
def admin_recent_events(
    limit: int = 50,
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
):
    _require_key(x_api_key)
    return {"items": list_recent_events(limit)}


@app.get("/admin/webhook-queue")
def admin_webhook_queue(
    limit: int = 50,
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
):
    _require_key(x_api_key)
    return {"items": list_webhook_queue(limit)}
