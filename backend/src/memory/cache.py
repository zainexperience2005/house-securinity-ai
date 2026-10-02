"""src/memory/cache.py - Redis Cache Layer for House Scrutiny AI.

Provides a thin, failure-tolerant Redis caching layer on top of the Neon
PostgreSQL queries.  All cache operations silently degrade to no-ops if Redis
is unavailable — the app always falls through to the DB.

TTLs (seconds):
  - thread_record    : 300  (5 min)  — refreshed on write
  - thread_list      : 30   (30 s)   — invalidated on new scrutiny / delete
  - chat_messages    : 20   (20 s)   — invalidated on new message
  - ai_models        : 600  (10 min) — rarely changes
"""

import json
import logging
from typing import Any

from src.config.settings import settings

logger = logging.getLogger(__name__)

# ── TTLs ──────────────────────────────────────────────────────────────────────
TTL_THREAD_RECORD = 300
TTL_THREAD_LIST = 30
TTL_CHAT_MESSAGES = 20
TTL_AI_MODELS = 600


# ── Cache key helpers ─────────────────────────────────────────────────────────
def _key_thread(thread_id: str) -> str:
    return f"hs:thread:{thread_id}"


def _key_thread_list() -> str:
    return "hs:threads:list"


def _key_chat(thread_id: str) -> str:
    return f"hs:chat:{thread_id}"


def _key_models() -> str:
    return "hs:models"


# ── Redis client (lazy singleton) ─────────────────────────────────────────────
_redis_client = None
_redis_failed = False  # stop spamming connection errors


def get_redis():
    """Return a live Redis client, or None if unavailable."""
    global _redis_client, _redis_failed
    if _redis_failed:
        return None
    if _redis_client is not None:
        return _redis_client
    try:
        import redis as _redis

        url = getattr(settings, "redis_url", None) or "redis://red-dav42tu0tbcc73dh444g:6379"
        client = _redis.from_url(url, decode_responses=True, socket_connect_timeout=2)
        client.ping()
        _redis_client = client
        msg = f"[REDIS] Connected successfully: {url}"
        logger.info(msg)
        print(msg, flush=True)
        return _redis_client
    except Exception as exc:
        msg = f"[REDIS] Connection failed ({exc}); caching disabled."
        logger.warning(msg)
        print(msg, flush=True)
        _redis_failed = True
        return None


# ── Generic helpers ───────────────────────────────────────────────────────────
def cache_get(key: str) -> Any | None:
    """Return deserialized value from Redis, or None on miss / error."""
    r = get_redis()
    if r is None:
        return None
    try:
        raw = r.get(key)
        return json.loads(raw) if raw is not None else None
    except Exception as exc:
        logger.debug(f"Redis GET error ({key}): {exc}")
        return None


def cache_set(key: str, value: Any, ttl: int) -> None:
    """Serialize and store value in Redis with the given TTL."""
    r = get_redis()
    if r is None:
        return
    try:
        r.setex(key, ttl, json.dumps(value, default=str))
    except Exception as exc:
        logger.debug(f"Redis SET error ({key}): {exc}")


def cache_delete(*keys: str) -> None:
    """Delete one or more keys from Redis."""
    r = get_redis()
    if r is None:
        return
    try:
        r.delete(*keys)
    except Exception as exc:
        logger.debug(f"Redis DEL error ({keys}): {exc}")


# ── Domain-specific cache helpers ─────────────────────────────────────────────
def get_cached_thread(thread_id: str) -> Any | None:
    return cache_get(_key_thread(thread_id))


def set_cached_thread(thread_id: str, record: Any) -> None:
    cache_set(_key_thread(thread_id), record, TTL_THREAD_RECORD)


def invalidate_thread(thread_id: str) -> None:
    cache_delete(_key_thread(thread_id), _key_thread_list())


def get_cached_thread_list() -> Any | None:
    return cache_get(_key_thread_list())


def set_cached_thread_list(data: Any) -> None:
    cache_set(_key_thread_list(), data, TTL_THREAD_LIST)


def invalidate_thread_list() -> None:
    cache_delete(_key_thread_list())


def get_cached_chat(thread_id: str) -> Any | None:
    return cache_get(_key_chat(thread_id))


def set_cached_chat(thread_id: str, messages: Any) -> None:
    cache_set(_key_chat(thread_id), messages, TTL_CHAT_MESSAGES)


def invalidate_chat(thread_id: str) -> None:
    cache_delete(_key_chat(thread_id))


def get_cached_models() -> Any | None:
    return cache_get(_key_models())


def set_cached_models(models: Any) -> None:
    cache_set(_key_models(), models, TTL_AI_MODELS)


def invalidate_models() -> None:
    cache_delete(_key_models())
