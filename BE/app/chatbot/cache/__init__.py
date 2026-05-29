from __future__ import annotations

import hashlib, json, time, logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── TTL config (giây) ─────────────────────────────────────────
TTL_MAP = {
    "DB_REVENUE":        60,
    "DB_ORDERS":         30,
    "DB_STOCK":          120,
    "DB_TOP_PRODUCTS":   120,
    "DB_SLOW_PRODUCTS":  300,
    "DB_IMPORT":         120,
    "DB_PRODUCT_INFO":   180,
    "DB_CATEGORY":       300,
    "DB_USERS":          300,
    "DB_USER_ANALYTICS": 120,
    "DB_PRODUCT_BY_DAY": 60,
    "default":           60,
}


def _make_key(intent: str, period_label: str, extra: str = "") -> str:
    raw = f"{intent}:{period_label}:{extra}"
    h   = hashlib.md5(raw.encode()).hexdigest()[:12]
    return f"chatbot:{intent}:{h}"


# ── In-memory fallback (dict + expiry) ────────────────────────
_mem: dict[str, tuple[Any, float]] = {}   # key → (value, expire_ts)


def _mem_get(key: str) -> Optional[Any]:
    entry = _mem.get(key)
    if entry and time.time() < entry[1]:
        return entry[0]
    _mem.pop(key, None)
    return None


def _mem_set(key: str, value: Any, ttl: int) -> None:
    _mem[key] = (value, time.time() + ttl)


# ── Redis client (lazy init) ───────────────────────────────────
_redis_client = None
_redis_ok     = False


def _get_redis():
    global _redis_client, _redis_ok
    if _redis_client is not None:
        return _redis_client if _redis_ok else None
    try:
        import redis
        r = redis.Redis(host="localhost", port=6379, db=0,
                        socket_connect_timeout=1, socket_timeout=1,
                        decode_responses=True)
        r.ping()
        _redis_client = r
        _redis_ok     = True
        logger.info("✅ Redis connected")
    except Exception as e:
        _redis_client = None
        _redis_ok     = False
        logger.info(f"⚠️  Redis unavailable ({e}), using in-memory cache")
    return _redis_client if _redis_ok else None


# ── Public API ─────────────────────────────────────────────────
def cache_get(intent: str, period_label: str, extra: str = "") -> Optional[dict]:
    key = _make_key(intent, period_label, extra)
    r   = _get_redis()
    if r:
        try:
            raw = r.get(key)
            if raw:
                return json.loads(raw)
        except Exception:
            pass
    return _mem_get(key)


def cache_set(intent: str, period_label: str, value: dict, extra: str = "") -> None:
    key = _make_key(intent, period_label, extra)
    ttl = TTL_MAP.get(intent, TTL_MAP["default"])
    r   = _get_redis()
    if r:
        try:
            r.setex(key, ttl, json.dumps(value, ensure_ascii=False, default=str))
            return
        except Exception:
            pass
    _mem_set(key, value, ttl)


def cache_invalidate(intent: str) -> None:
    r = _get_redis()
    if r:
        try:
            pattern = f"chatbot:{intent}:*"
            keys    = r.keys(pattern)
            if keys:
                r.delete(*keys)
            return
        except Exception:
            pass
    # in-memory: xóa theo prefix
    for k in list(_mem.keys()):
        if k.startswith(f"chatbot:{intent}:"):
            _mem.pop(k, None)
