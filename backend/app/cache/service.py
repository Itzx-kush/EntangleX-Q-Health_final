from __future__ import annotations

from collections import OrderedDict
import json
import logging
import threading
import time
from typing import Any, Callable

from ..config import get_settings

logger = logging.getLogger("qhealth.cache")


class InMemoryCache:
    """Thread-safe bounded in-process LRU cache with TTL expiration.

    Never stores authentication tokens, secrets, or raw biomedical payloads.
    """

    def __init__(self, max_entries: int = 2000, default_ttl_seconds: float = 300.0):
        self.lock = threading.RLock()
        self.max_entries = max_entries
        self.default_ttl = default_ttl_seconds
        # Maps key -> (value, expires_at, created_at)
        self._store: OrderedDict[str, tuple[Any, float, float]] = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key: str) -> Any | None:
        now = time.time()
        with self.lock:
            if key not in self._store:
                self._misses += 1
                return None
            value, expires_at, _ = self._store[key]
            if now > expires_at:
                del self._store[key]
                self._misses += 1
                return None
            # Move to end for LRU freshness
            self._store.move_to_end(key)
            self._hits += 1
            return value

    def set(self, key: str, value: Any, ttl_seconds: float | None = None) -> None:
        now = time.time()
        ttl = self.default_ttl if ttl_seconds is None else ttl_seconds
        expires_at = now + ttl
        with self.lock:
            if key in self._store:
                self._store.move_to_end(key)
            else:
                while len(self._store) >= self.max_entries:
                    self._store.popitem(last=False)
                    self._evictions += 1
            self._store[key] = (value, expires_at, now)

    def delete(self, key: str) -> bool:
        with self.lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def invalidate_prefix(self, prefix: str) -> int:
        with self.lock:
            keys_to_remove = [k for k in self._store if k.startswith(prefix)]
            for k in keys_to_remove:
                del self._store[k]
            return len(keys_to_remove)

    def clear(self) -> None:
        with self.lock:
            self._store.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> dict[str, Any]:
        with self.lock:
            total = self._hits + self._misses
            hit_rate = round(self._hits / total, 4) if total > 0 else 0.0
            return {
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
                "hit_ratio_pct": round(hit_rate * 100.0, 1),
                "evictions": self._evictions,
                "size": len(self._store),
                "max_entries": self.max_entries,
            }


class PluggableCache:
    """High-level caching service with in-memory authority and optional Redis acceleration."""

    def __init__(self, redis_enabled: bool | None = None):
        settings = get_settings()
        self._redis_enabled_override = redis_enabled
        self.memory = InMemoryCache(
            max_entries=settings.cache_max_entries,
            default_ttl_seconds=settings.cache_ttl_seconds,
        )

    def _is_redis_enabled(self) -> bool:
        if self._redis_enabled_override is not None:
            return self._redis_enabled_override
        return get_settings().redis_enabled

    def get(self, key: str) -> Any | None:
        settings = get_settings()
        if not settings.cache_enabled:
            return None
        # Always check in-memory first for maximum speed
        val = self.memory.get(key)
        if val is not None:
            return val

        # Optional Redis acceleration if enabled and available
        if self._is_redis_enabled():
            try:
                from ..redis_bridge import execute_command
                redis_val = execute_command(settings, ["GET", key])
                if redis_val is not None and isinstance(redis_val, str):
                    try:
                        parsed = json.loads(redis_val)
                        # Backfill into in-memory cache for fast local lookup
                        self.memory.set(key, parsed)
                        return parsed
                    except Exception:
                        pass
            except Exception:
                # Graceful degradation: never fail research request if Redis is offline/slow
                pass

        return None

    def set(self, key: str, value: Any, ttl_seconds: float | None = None) -> None:
        settings = get_settings()
        if not settings.cache_enabled:
            return
        self.memory.set(key, value, ttl_seconds=ttl_seconds)

        if self._is_redis_enabled():
            try:
                from ..redis_bridge import execute_command
                serialized = json.dumps(value)
                execute_command(settings, ["SET", key, serialized])
            except Exception:
                # Redis failure is non-fatal; memory cache remains authoritative
                pass

    def delete(self, key: str) -> bool:
        return self.memory.delete(key)

    def invalidate_prefix(self, prefix: str) -> int:
        return self.memory.invalidate_prefix(prefix)

    def stats(self) -> dict[str, Any]:
        stats = self.memory.stats()
        stats["cache_backend"] = "redis" if self._is_redis_enabled() else "in_memory"
        return stats

    def reset(self) -> None:
        self.memory.clear()


# Global cache instance
cache = PluggableCache()


def deterministic_cache_key(resource_type: str, resource_id: str, fingerprint: str | None = None) -> str:
    """Generate a safe, collision-resistant cache key."""
    if fingerprint:
        return f"{resource_type}:{resource_id}:{fingerprint}"
    return f"{resource_type}:{resource_id}"
