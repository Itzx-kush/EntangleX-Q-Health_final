from __future__ import annotations

from collections import deque
import re
import threading
import time
from typing import Any
import numpy as np

_UUID_PATTERN = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
_HASH_PATTERN = re.compile(r"\b[0-9a-fA-F]{64}\b")


class RequestMetric:
    """Thread-safe bounded in-process metric collector for request latencies and counts."""

    def __init__(self, max_samples: int = 1000):
        self.lock = threading.Lock()
        self.max_samples = max_samples
        self.total_count = 0
        self.error_count = 0
        # Ring buffer of (timestamp, duration_ms, is_error)
        self.samples: deque[tuple[float, float, bool]] = deque(maxlen=max_samples)

    def record(self, duration_ms: float, is_error: bool) -> None:
        now = time.time()
        with self.lock:
            self.total_count += 1
            if is_error:
                self.error_count += 1
            self.samples.append((now, float(duration_ms), is_error))

    def stats(self, window_seconds: float | None = None) -> dict[str, Any]:
        now = time.time()
        with self.lock:
            if window_seconds is not None and window_seconds > 0:
                cutoff = now - window_seconds
                filtered = [s for s in self.samples if s[0] >= cutoff]
            else:
                filtered = list(self.samples)

            if not filtered:
                return {
                    "total": 0,
                    "errors": 0,
                    "error_rate": 0.0,
                    "avg_ms": 0.0,
                    "p50_ms": 0.0,
                    "p95_ms": 0.0,
                    "p99_ms": 0.0,
                }

            latencies = [s[1] for s in filtered]
            total_samples = len(filtered)
            error_samples = sum(1 for s in filtered if s[2])
            error_rate = round(error_samples / total_samples, 4) if total_samples > 0 else 0.0
            avg_ms = round(float(np.mean(latencies)), 2)
            p50_ms = round(float(np.percentile(latencies, 50)), 2)
            p95_ms = round(float(np.percentile(latencies, 95)), 2)
            p99_ms = round(float(np.percentile(latencies, 99)), 2)

            return {
                "total": total_samples,
                "errors": error_samples,
                "error_rate": error_rate,
                "avg_ms": avg_ms,
                "p50_ms": p50_ms,
                "p95_ms": p95_ms,
                "p99_ms": p99_ms,
            }

    def lifetime_counts(self) -> tuple[int, int]:
        with self.lock:
            return self.total_count, self.error_count

    def reset(self) -> None:
        with self.lock:
            self.total_count = 0
            self.error_count = 0
            self.samples.clear()


class TelemetryRegistry:
    """Bounded, thread-safe in-process telemetry registry with route normalization."""

    def __init__(
        self,
        max_routes: int = 150,
        max_samples: int = 1000,
        max_recent_samples: int | None = None,
    ):
        samples_bound = max_recent_samples if max_recent_samples is not None else max_samples
        self.lock = threading.Lock()
        self.max_routes = max_routes
        self.max_samples = samples_bound
        self.start_time = time.time()
        self.global_metric = RequestMetric(max_samples=samples_bound)
        self.route_metrics: dict[str, RequestMetric] = {}

    @staticmethod
    def normalize_route(method: str, path: str) -> str:
        """Normalize dynamic path parameters to avoid unbounded metric cardinality."""
        clean_path = path.split("?")[0] if "?" in path else path
        normalized = _UUID_PATTERN.sub("{id}", clean_path)
        normalized = _HASH_PATTERN.sub("{hash}", normalized)
        # Normalize numeric IDs in query/paths if solitary
        normalized = re.sub(r"/(\d+)(?=/|$)", r"/{id}", normalized)
        # Strip trailing slash if not root
        if len(normalized) > 1 and normalized.endswith("/"):
            normalized = normalized[:-1]
        return f"{method.upper()} {normalized}"

    def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        request_id: str | None = None,
    ) -> None:
        is_error = status_code >= 400
        self.global_metric.record(duration_ms, is_error)

        route_key = self.normalize_route(method, path)
        with self.lock:
            if route_key not in self.route_metrics:
                if len(self.route_metrics) >= self.max_routes:
                    # Bound memory: drop the least-active route or fallback to common bucket
                    route_key = f"{method.upper()} /*"
                    if route_key not in self.route_metrics:
                        self.route_metrics[route_key] = RequestMetric(max_samples=self.max_samples)
                else:
                    self.route_metrics[route_key] = RequestMetric(max_samples=self.max_samples)
            metric = self.route_metrics[route_key]

        metric.record(duration_ms, is_error)

    def uptime_seconds(self) -> float:
        return round(time.time() - self.start_time, 1)

    def get_summary(self, window_seconds: float | None = None) -> dict[str, Any]:
        global_stats = self.global_metric.stats(window_seconds)
        lifetime_total, lifetime_errors = self.global_metric.lifetime_counts()

        with self.lock:
            route_items = list(self.route_metrics.items())

        by_route: dict[str, Any] = {}
        for route_key, metric in route_items:
            route_stats = metric.stats(window_seconds)
            if route_stats["total"] > 0:
                by_route[route_key] = route_stats

        return {
            "uptime_seconds": self.uptime_seconds(),
            "window_seconds": window_seconds,
            "requests": {
                **global_stats,
                "lifetime_total": lifetime_total,
                "lifetime_errors": lifetime_errors,
            },
            "by_route": by_route,
        }

    def reset(self) -> None:
        self.start_time = time.time()
        self.global_metric.reset()
        with self.lock:
            self.route_metrics.clear()


# Global in-process telemetry singleton
telemetry_registry = TelemetryRegistry()
