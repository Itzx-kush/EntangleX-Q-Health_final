from __future__ import annotations

from collections import OrderedDict, deque
import hashlib
import threading
import time
from typing import Tuple
from fastapi import Request

from ..config import get_settings
from ..utils.errors import AppError


class SlidingWindowRateLimiter:
    """Bounded, thread-safe in-process sliding window rate limiter.

    Guards expensive endpoints against accidental unbounded request floods
    without requiring external infrastructure like Redis or token buckets.
    """

    def __init__(
        self,
        max_requests: int = 30,
        window_seconds: int = 60,
        max_identities: int = 5000,
    ):
        self.lock = threading.Lock()
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.max_identities = max_identities
        # Maps client_id -> deque of request timestamps
        self._clients: OrderedDict[str, deque[float]] = OrderedDict()

    def check(self, identity: str, cost: int = 1) -> Tuple[bool, int, float]:
        """Check if an identity has capacity. Returns (allowed, remaining, retry_after_seconds)."""
        now = time.time()
        cutoff = now - self.window_seconds

        with self.lock:
            if identity not in self._clients:
                # Evict oldest inactive client identity if at capacity
                while len(self._clients) >= self.max_identities:
                    self._clients.popitem(last=False)
                self._clients[identity] = deque()

            timestamps = self._clients[identity]
            self._clients.move_to_end(identity)

            # Evict timestamps outside the window
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()

            current_count = len(timestamps)
            if current_count + cost > self.max_requests:
                oldest = timestamps[0] if timestamps else now
                retry_after = max(1.0, round((oldest + self.window_seconds) - now, 1))
                return False, 0, retry_after

            for _ in range(cost):
                timestamps.append(now)

            remaining = max(0, self.max_requests - len(timestamps))
            return True, remaining, 0.0

    def reset(self) -> None:
        with self.lock:
            self._clients.clear()


# Global in-process rate limiter for expensive endpoints
_expensive_limiter: SlidingWindowRateLimiter | None = None
_limiter_lock = threading.Lock()


def get_expensive_limiter() -> SlidingWindowRateLimiter:
    global _expensive_limiter
    if _expensive_limiter is None:
        with _limiter_lock:
            if _expensive_limiter is None:
                settings = get_settings()
                _expensive_limiter = SlidingWindowRateLimiter(
                    max_requests=settings.rate_limit_max_requests,
                    window_seconds=settings.rate_limit_window_seconds,
                )
    return _expensive_limiter


def _safe_client_identity(request: Request) -> str:
    """Derive a bounded, privacy-safe identity hash from request attributes."""
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        # Hash the bearer token so the token itself is never stored or reflected
        token_hash = hashlib.sha256(auth[7:].encode()).hexdigest()[:16]
        return f"token:{token_hash}"

    client_ip = request.client.host if request.client else "unknown"
    return f"ip:{client_ip}"


async def rate_limit_expensive(request: Request) -> None:
    """FastAPI dependency for expensive endpoints (training, AI, upload, multi-seed studies).

    Harmless metadata reads are never rate limited.
    """
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return

    limiter = get_expensive_limiter()
    identity = _safe_client_identity(request)
    allowed, remaining, retry_after = limiter.check(identity)

    if not allowed:
        request_id = getattr(request.state, "request_id", None)
        raise AppError(
            "rate_limited",
            f"Rate limit exceeded for expensive operations. Please retry after {retry_after} seconds.",
            status=429,
        )
