from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from security import (
    generate_api_key,
    insert_api_key,
    list_api_keys,
    is_valid_api_key,
    has_any_api_key,
)

router = APIRouter(prefix="/admin/api-keys", tags=["API Keys"])


def _require_key(x_api_key: str | None):
    if not x_api_key or not is_valid_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")


class CreateKeyPayload(BaseModel):
    name: str


@router.get("")
def get_api_keys(x_api_key: str | None = Header(default=None, alias="x-api-key")):
    _require_key(x_api_key)
    return {"items": list_api_keys()}


@router.post("")
def create_api_key(
    payload: CreateKeyPayload,
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
):
    # ✅ BOOTSTRAP MODE
    if has_any_api_key():
        _require_key(x_api_key)

    raw_key = generate_api_key()
    insert_api_key(raw_key, payload.name)

    return {
        "key": raw_key,  # shown ONCE
        "name": payload.name,
    }
