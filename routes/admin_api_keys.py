from fastapi import APIRouter, Header, HTTPException
import secrets
import time
from security import is_valid_api_key, insert_api_key, list_api_keys

router = APIRouter(prefix="/admin/api-keys", tags=["API Keys"])


def _require_key(x_api_key: str | None):
    if not x_api_key or not is_valid_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")


@router.get("")
def get_keys(x_api_key: str | None = Header(default=None, alias="x-api-key")):
    _require_key(x_api_key)
    return {"items": list_api_keys()}


@router.post("")
def create_key(
    payload: dict,
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
):
    _require_key(x_api_key)

    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Key name required")

    key = f"axf_{secrets.token_hex(16)}"
    insert_api_key(key, name)

    return {
        "key": key,
        "name": name,
        "created_at": int(time.time()),
    }
