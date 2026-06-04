"""Per-run circuit breaker for LLM calls.

The breaker is created once per DAG task invocation and shared across the
worker threads in ``classify_posts_batch`` / ``flag_scams``. When the
number of consecutive failures crosses ``threshold``, the breaker trips
and the caller stops issuing new LLM requests, falling back to the
rule-based path for the remainder of the run.

The breaker counts POST-retry failures only — tenacity should exhaust
its retry attempts before bubbling the exception up to ``record_failure``.
A single tenacity-handled retry burst should not contribute more than
one failure to the breaker count.
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)


class LLMCircuitBreaker:
    """Thread-safe consecutive-failure breaker."""

    def __init__(self, threshold: int = 5, name: str = "llm") -> None:
        if threshold < 1:
            raise ValueError("threshold must be >= 1")
        self.threshold = threshold
        self.name = name
        self._lock = threading.Lock()
        self._consecutive_failures = 0
        self._total_failures = 0
        self._total_successes = 0
        self._tripped = False

    # ── State transitions ──────────────────────────────────────────────────
    def record_success(self) -> None:
        with self._lock:
            self._consecutive_failures = 0
            self._total_successes += 1

    def record_failure(self, exc: Optional[BaseException] = None) -> None:
        with self._lock:
            self._consecutive_failures += 1
            self._total_failures += 1
            if not self._tripped and self._consecutive_failures >= self.threshold:
                self._tripped = True
                logger.warning(
                    "Circuit breaker %r TRIPPED after %d consecutive failures (last: %s)",
                    self.name, self._consecutive_failures, exc,
                )

    def force_trip(self, reason: str = "") -> None:
        """Trip the breaker immediately (e.g., when the API key is missing)."""
        with self._lock:
            if not self._tripped:
                self._tripped = True
                logger.warning("Circuit breaker %r FORCE-TRIPPED: %s", self.name, reason)

    # ── Observers ──────────────────────────────────────────────────────────
    def is_tripped(self) -> bool:
        with self._lock:
            return self._tripped

    @property
    def consecutive_failures(self) -> int:
        with self._lock:
            return self._consecutive_failures

    @property
    def total_failures(self) -> int:
        with self._lock:
            return self._total_failures

    @property
    def total_successes(self) -> int:
        with self._lock:
            return self._total_successes

    def status_message(self) -> str:
        with self._lock:
            if self._tripped:
                return (
                    f"breaker={self.name!r} TRIPPED "
                    f"(failures={self._total_failures} successes={self._total_successes})"
                )
            return (
                f"breaker={self.name!r} OK "
                f"(consecutive_fail={self._consecutive_failures}/{self.threshold} "
                f"total_fail={self._total_failures} total_ok={self._total_successes})"
            )
