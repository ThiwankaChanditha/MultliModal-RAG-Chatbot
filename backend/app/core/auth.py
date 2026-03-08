import os
import firebase_admin
from firebase_admin import credentials, auth
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# ── Firebase init ─────────────────────────────────────────────────────────────
_cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "firebase-service-account.json")

if not firebase_admin._apps:
    cred = credentials.Certificate(_cred_path)
    firebase_admin.initialize_app(cred)

security = HTTPBearer()

# ── Owner config ──────────────────────────────────────────────────────────────
# Set this to your Firebase UID in .env
OWNER_UID = os.getenv("OWNER_UID", "")
QUERY_LIMIT = int(os.getenv("QUERY_LIMIT", "5"))

# ── Query count store ─────────────────────────────────────────────────────────
# Uses Redis if REDIS_URL is set, otherwise falls back to in-memory dict.
# In-memory resets on server restart — fine for dev, use Redis for production.

def _get_store():
    """Return a store object with get(key) and incr(key) methods."""
    from app.core.config import settings

    if settings.REDIS_URL:
        try:
            import redis
            r = redis.from_url(settings.REDIS_URL, decode_responses=True)
            r.ping()  # test connection
            return _RedisStore(r)
        except Exception as e:
            print(f"Redis unavailable ({e}), falling back to in-memory store")

    return _MemoryStore()


class _RedisStore:
    def __init__(self, client):
        self._r = client

    def get(self, key: str) -> int:
        val = self._r.get(f"query_count:{key}")
        return int(val) if val else 0

    def incr(self, key: str) -> int:
        return self._r.incr(f"query_count:{key}")


class _MemoryStore:
    def __init__(self):
        self._counts: dict[str, int] = {}

    def get(self, key: str) -> int:
        return self._counts.get(key, 0)

    def incr(self, key: str) -> int:
        self._counts[key] = self._counts.get(key, 0) + 1
        return self._counts[key]


# Single shared store instance
_store = _get_store()


# ── Token verification + rate limiting ───────────────────────────────────────

def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> dict:
    """
    FastAPI dependency — verifies Firebase ID token.
    For non-owners, enforces a QUERY_LIMIT per UID.
    Returns the decoded token payload (contains uid, email, etc.)
    """
    try:
        decoded = auth.verify_id_token(credentials.credentials)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {e}")

    uid = decoded.get("uid", "")

    # Owner bypasses all limits
    if uid == OWNER_UID:
        decoded["is_owner"] = True
        decoded["queries_used"] = None
        decoded["queries_remaining"] = None
        return decoded

    # Non-owner: check and increment count
    current = _store.get(uid)
    if current >= QUERY_LIMIT:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "query_limit_reached",
                "message": f"You have used all {QUERY_LIMIT} free queries.",
                "queries_used": current,
                "queries_remaining": 0,
            },
        )

    new_count = _store.incr(uid)
    decoded["is_owner"] = False
    decoded["queries_used"] = new_count
    decoded["queries_remaining"] = QUERY_LIMIT - new_count
    return decoded


def verify_token_no_limit(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> dict:
    """
    Use this for routes that need auth but should NOT count toward the query limit
    (e.g. /upload). Only verifies the token.
    """
    try:
        decoded = auth.verify_id_token(credentials.credentials)
        return decoded
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {e}")


def get_query_count(uid: str) -> dict:
    """Helper to check a user's current count without incrementing."""
    if uid == OWNER_UID:
        return {"is_owner": True, "queries_used": None, "queries_remaining": None}
    count = _store.get(uid)
    return {
        "is_owner": False,
        "queries_used": count,
        "queries_remaining": max(0, QUERY_LIMIT - count),
    }