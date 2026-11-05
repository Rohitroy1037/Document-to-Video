import unittest

from fastapi import HTTPException

from app.utils.rate_limit import SlidingWindowRateLimiter


class SlidingWindowRateLimiterTests(unittest.TestCase):
    def test_limit_is_shared_by_scope(self):
        limiter = SlidingWindowRateLimiter()

        limiter.check("generation", limit=2, window_seconds=60, now=0)
        limiter.check("generation", limit=2, window_seconds=60, now=10)

        with self.assertRaises(HTTPException) as raised:
            limiter.check("generation", limit=2, window_seconds=60, now=20)

        self.assertEqual(raised.exception.status_code, 429)
        self.assertEqual(raised.exception.headers["Retry-After"], "40")

    def test_expired_requests_do_not_count(self):
        limiter = SlidingWindowRateLimiter()

        limiter.check("upload", limit=1, window_seconds=60, now=0)
        limiter.check("upload", limit=1, window_seconds=60, now=60)

    def test_limits_are_independent_by_scope(self):
        limiter = SlidingWindowRateLimiter()

        limiter.check("upload", limit=1, window_seconds=60, now=0)
        limiter.check("chat", limit=1, window_seconds=60, now=0)


if __name__ == "__main__":
    unittest.main()
