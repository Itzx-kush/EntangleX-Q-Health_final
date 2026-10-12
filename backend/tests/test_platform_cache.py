import time
import pytest
from app.cache.service import InMemoryCache, PluggableCache, cache
from app.data.catalog import list_builtin_datasets


def test_in_memory_cache_basic_ops():
    c = InMemoryCache(default_ttl_seconds=10.0, max_entries=100)
    assert c.get("nonexistent") is None

    c.set("k1", {"foo": "bar"})
    assert c.get("k1") == {"foo": "bar"}

    c.delete("k1")
    assert c.get("k1") is None


def test_in_memory_cache_ttl_expiration():
    c = InMemoryCache(default_ttl_seconds=0.05, max_entries=100)
    c.set("expiring", "value", ttl_seconds=0.05)
    assert c.get("expiring") == "value"

    time.sleep(0.08)
    assert c.get("expiring") is None


def test_in_memory_cache_prefix_invalidation():
    c = InMemoryCache(default_ttl_seconds=60.0, max_entries=100)
    c.set("study:1:run", {"data": 1})
    c.set("study:1:metrics", {"data": 2})
    c.set("study:2:run", {"data": 3})

    evicted = c.invalidate_prefix("study:1:")
    assert evicted == 2
    assert c.get("study:1:run") is None
    assert c.get("study:1:metrics") is None
    assert c.get("study:2:run") == {"data": 3}


def test_in_memory_cache_lru_eviction():
    c = InMemoryCache(default_ttl_seconds=60.0, max_entries=3)
    c.set("a", 1)
    c.set("b", 2)
    c.set("c", 3)
    # Access 'a' to make it recently used
    assert c.get("a") == 1
    # Adding 'd' should evict 'b' (the least recently used)
    c.set("d", 4)

    assert c.get("b") is None
    assert c.get("a") == 1
    assert c.get("c") == 3
    assert c.get("d") == 4
    stats = c.stats()
    assert stats["evictions"] >= 1


def test_cache_stats_tracking():
    c = InMemoryCache(default_ttl_seconds=60.0, max_entries=100)
    c.set("x", 42)
    # 2 hits
    c.get("x")
    c.get("x")
    # 1 miss
    c.get("missing")

    stats = c.stats()
    assert stats["hits"] == 2
    assert stats["misses"] == 1
    assert stats["hit_ratio_pct"] == pytest.approx(66.7, abs=0.5)


def test_pluggable_cache_graceful_degradation():
    # PluggableCache with no redis should safely execute in-memory
    pc = PluggableCache(redis_enabled=False)
    pc.set("key", "val")
    assert pc.get("key") == "val"
    stats = pc.stats()
    assert stats["cache_backend"] == "in_memory"


def test_catalog_caching():
    # Calling list_builtin_datasets should populate cache
    first_call = list_builtin_datasets(include_readiness=False)
    assert len(first_call) == 5

    # Second call should return from cache
    second_call = list_builtin_datasets(include_readiness=False)
    assert first_call == second_call
