from collections import defaultdict, deque
from math import ceil
from threading import Lock
from time import monotonic

from fastapi import HTTPException


class SlidingWindowRateLimiter:
    def __init__(self):
        self._requests = defaultdict(deque)
        self._lock = Lock()

    def check(
        self,
        scope: str,
        limit: int,
        window_seconds: int,
        now: float | None = None,
    ) -> None:
        current_time = monotonic() if now is None else now
        cutoff = current_time - window_seconds

        with self._lock:
            requests = self._requests[scope]
            while requests and requests[0] <= cutoff:
                requests.popleft()

            if len(requests) >= limit:
                retry_after = max(
                    1,
                    ceil(window_seconds - (current_time - requests[0])),
                )
                raise HTTPException(
                    status_code=429,
                    detail="This public demo has reached its request limit. Try again later.",
                    headers={"Retry-After": str(retry_after)},
                )

            requests.append(current_time)


_limiter = SlidingWindowRateLimiter()
_WINDOW_SECONDS = 60 * 60


def rate_limit(scope: str, limit: int):
    def dependency() -> None:
        _limiter.check(scope, limit, _WINDOW_SECONDS)

    return dependency
