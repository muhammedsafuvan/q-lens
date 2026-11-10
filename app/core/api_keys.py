import hashlib
import secrets


def get_api_key_prefix(app_env: str) -> str:
    return "ql_live_" if app_env.strip().lower() == "production" else "ql_test_"


def generate_api_key(app_env: str) -> tuple[str, str]:
    prefix = get_api_key_prefix(app_env)
    plaintext_key = f"{prefix}{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(plaintext_key.encode()).hexdigest()

    return plaintext_key, key_hash
