"""
A simple in-memory metrics tracker. Like the Phase 4 job store, this is
process-local - sufficient for single-instance local/small deployments.
Multi-instance production monitoring would use a real metrics backend
(Prometheus, Datadog, etc.), which is a reasonable future upgrade beyond
this project's current scale.
"""
import time
from collections import defaultdict
from threading import Lock

_lock = Lock()
_request_counts: dict[str, int] = defaultdict(int)
_failure_counts: dict[str, int] = defaultdict(int)
_llm_latencies_ms: list[float] = []
_started_at = time.time()


def record_request(endpoint: str) -> None:
    with _lock:
        _request_counts[endpoint] += 1


def record_failure(endpoint: str) -> None:
    with _lock:
        _failure_counts[endpoint] += 1


def record_llm_latency(latency_ms: float) -> None:
    with _lock:
        _llm_latencies_ms.append(latency_ms)
        # Keep only the most recent 500 to bound memory usage.
        if len(_llm_latencies_ms) > 500:
            _llm_latencies_ms.pop(0)


def get_metrics_snapshot() -> dict:
    with _lock:
        avg_latency = (
            sum(_llm_latencies_ms) / len(_llm_latencies_ms) if _llm_latencies_ms else None
        )
        return {
            "uptime_seconds": round(time.time() - _started_at, 1),
            "request_counts": dict(_request_counts),
            "failure_counts": dict(_failure_counts),
            "llm_avg_latency_ms": round(avg_latency, 1) if avg_latency is not None else None,
            "llm_calls_tracked": len(_llm_latencies_ms),
        }