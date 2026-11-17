"""Request timing and body-size limits.

Latency samples are kept in memory (last 5,000 requests since the server
started). They reset on restart; this is stated in the Analytics UI.
"""

import statistics
import threading
import time
from collections import deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class LatencyTracker:
    def __init__(self, max_samples: int = 5000) -> None:
        self._samples: deque[tuple[str, int, float]] = deque(maxlen=max_samples)
        self._lock = threading.Lock()

    def record(self, route: str, status_code: int, duration_ms: float) -> None:
        with self._lock:
            self._samples.append((route, status_code, duration_ms))

    def summary(self) -> dict:
        with self._lock:
            samples = list(self._samples)
        if not samples:
            return {"count": 0, "avg_ms": None, "p50_ms": None, "p95_ms": None, "routes": []}
        durations = sorted(s[2] for s in samples)
        by_route: dict[str, list[float]] = {}
        for route, _, ms in samples:
            by_route.setdefault(route, []).append(ms)
        routes = sorted(
            ({"route": r, "count": len(v), "avg_ms": round(statistics.fmean(v), 2)}
             for r, v in by_route.items()),
            key=lambda item: item["count"], reverse=True,
        )[:10]
        return {
            "count": len(samples),
            "avg_ms": round(statistics.fmean(durations), 2),
            "p50_ms": round(durations[len(durations) // 2], 2),
            "p95_ms": round(durations[min(len(durations) - 1, int(len(durations) * 0.95))], 2),
            "error_rate": round(sum(1 for s in samples if s[1] >= 500) / len(samples), 4),
            "routes": routes,
            "note": "In-memory sample of recent requests since the server started.",
        }


latency_tracker = LatencyTracker()


class MetricsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_body_bytes: int):
        super().__init__(app)
        self.max_body_bytes = max_body_bytes

    async def dispatch(self, request: Request, call_next):
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > self.max_body_bytes:
            return JSONResponse(status_code=413, content={
                "success": False,
                "error": {"code": "HTTP_413", "message": "Request body too large."}})
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - started) * 1000
        route = request.scope.get("route")
        path = getattr(route, "path", None) or "unmatched"
        if path.startswith("/api") or path == "/health":
            latency_tracker.record(f"{request.method} {path}", response.status_code, duration_ms)
        response.headers["X-Response-Time-ms"] = f"{duration_ms:.1f}"
        return response
