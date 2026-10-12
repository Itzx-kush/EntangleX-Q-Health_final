import time
import pytest
from starlette.requests import Request
from app.config import get_settings
from app.ratelimit.limiter import SlidingWindowRateLimiter, rate_limit_expensive, get_expensive_limiter
from app.utils.errors import AppError


def test_sliding_window_limiter_basic_capacity():
    limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=60)
    client_id = "client_alpha"

    # 1st request
    allowed, rem, retry = limiter.check(client_id)
    assert allowed is True
    assert rem == 2
    assert retry == 0.0

    # 2nd request
    allowed, rem, retry = limiter.check(client_id)
    assert allowed is True
    assert rem == 1

    # 3rd request
    allowed, rem, retry = limiter.check(client_id)
    assert allowed is True
    assert rem == 0

    # 4th request - should be blocked
    allowed, rem, retry = limiter.check(client_id)
    assert allowed is False
    assert rem == 0
    assert retry > 0.0


def test_sliding_window_limiter_client_isolation():
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=60)
    client_a = "client_a"
    client_b = "client_b"

    # Exhaust client A
    limiter.check(client_a)
    limiter.check(client_a)
    allowed_a, _, _ = limiter.check(client_a)
    assert allowed_a is False

    # Client B should still have full quota
    allowed_b, rem_b, _ = limiter.check(client_b)
    assert allowed_b is True
    assert rem_b == 1


def test_sliding_window_limiter_window_expiry():
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=1)
    client_id = "client_short"

    limiter.check(client_id)
    limiter.check(client_id)
    allowed, _, _ = limiter.check(client_id)
    assert allowed is False

    time.sleep(1.05)
    allowed, rem, _ = limiter.check(client_id)
    assert allowed is True
    assert rem == 1


def test_sliding_window_limiter_bounded_identities():
    limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=60, max_identities=3)
    limiter.check("id_1")
    limiter.check("id_2")
    limiter.check("id_3")
    assert len(limiter._clients) == 3

    # Adding a 4th identity should evict the oldest ("id_1")
    limiter.check("id_4")
    assert len(limiter._clients) == 3
    assert "id_1" not in limiter._clients
    assert "id_4" in limiter._clients


def test_rate_limit_expensive_dependency_blocks_at_threshold(monkeypatch):
    import asyncio
    test_limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=60)
    monkeypatch.setattr("app.ratelimit.limiter.get_expensive_limiter", lambda: test_limiter)

    # Build a minimal mock request
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/training/jobs",
        "headers": [(b"authorization", b"Bearer test-token-12345")],
        "client": ("127.0.0.1", 12345),
    }
    request = Request(scope)

    # First 2 requests should pass
    asyncio.run(rate_limit_expensive(request))
    asyncio.run(rate_limit_expensive(request))

    # 3rd request should raise AppError 429
    with pytest.raises(AppError) as exc_info:
        asyncio.run(rate_limit_expensive(request))
    assert exc_info.value.status == 429
    assert exc_info.value.code == "rate_limited"
