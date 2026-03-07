from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar


T = TypeVar("T")


def run_with_retry(func: Callable[[], T], attempts: int, backoff_seconds: float) -> T:
    if attempts < 1:
        attempts = 1

    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return func()
        except Exception as exc:  # pragma: no cover - final behavior covered by callers
            last_error = exc
            if attempt < attempts:
                time.sleep(backoff_seconds * attempt)

    if last_error is None:
        raise RuntimeError("retry_failed_without_exception")
    raise last_error
