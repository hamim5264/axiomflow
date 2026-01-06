import secrets
import hashlib

API_KEY_PREFIX = "axf_"


def generate_api_key() -> str:
    # Example: axf_AbCdEf...
    return API_KEY_PREFIX + secrets.token_urlsafe(32)


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def key_preview(raw_key: str) -> str:
    # Shows only a safe preview in dashboard
    if not raw_key:
        return ""
    head = raw_key[:10]
    tail = raw_key[-4:] if len(raw_key) > 14 else ""
    return f"{head}…{tail}"
