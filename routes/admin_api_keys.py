from fastapi import APIRouter, Header, HTTPException
from security import generate_api_key
from storage import is_valid_api_key, insert_api_key, list_api_keys, revoke_api_key

router = APIRouter()


def _require_key(x_api_key: str | None):
    if not x_api_key or not is_valid_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")


@router.get("/admin/api-keys")
def admin_list_api_keys(
    limit: int = 200,
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
):
    _require_key(x_api_key)
    return {"items": list_api_keys(limit)}


@router.post("/admin/api-keys")
def admin_create_api_key(
    payload: dict,
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
):
    _require_key(x_api_key)

    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    raw_key = generate_api_key()
    record = insert_api_key(raw_key, name)

    # IMPORTANT: raw key only returned once
    return record


@router.post("/admin/api-keys/{key_id}/revoke")
def admin_revoke_api_key(
    key_id: int,
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
):
    _require_key(x_api_key)
    revoke_api_key(key_id)
    return {"status": "revoked"}
