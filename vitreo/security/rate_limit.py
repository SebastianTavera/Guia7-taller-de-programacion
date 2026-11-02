"""In-memory sliding-window limiter of failed logins per account (brute-force protection).

Per-process state: with several workers, move it to a shared store such as Redis.
"""

import math
import time
from collections import deque
from collections.abc import Callable


class LoginAttemptLimiter:
    def __init__(
        self, max_attempts: int = 5, window_seconds: float = 300.0, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._clock = clock
        self._failures: dict[str, deque[float]] = {}

    def _recent_failures(self, key: str) -> deque[float]:
        failures = self._failures.get(key, deque())
        cutoff = self._clock() - self.window_seconds
        while failures and failures[0] <= cutoff:
            failures.popleft()
        if not failures:
            self._failures.pop(key, None)
        return failures

    def __len__(self) -> int:
        """Number of accounts with recent failures (memory stays bounded by the window)."""
        return len(self._failures)

    def is_blocked(self, key: str) -> bool:
        return len(self._recent_failures(key)) >= self.max_attempts

    def retry_after(self, key: str) -> int:
        """Seconds until the oldest failure leaves the window (0 when nothing is recorded)."""
        failures = self._recent_failures(key)
        if not failures:
            return 0
        return max(1, math.ceil(failures[0] + self.window_seconds - self._clock()))

    def register_failure(self, key: str) -> None:
        self._failures.setdefault(key, deque()).append(self._clock())

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)

    def clear(self) -> None:
        self._failures.clear()
