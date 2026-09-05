"""Token bucket rate limiter for SEC EDGAR API compliance."""

import asyncio
import time


class AsyncTokenBucket:
    """Thread/task-safe async token bucket rate limiter.

    Enforces the SEC EDGAR fair access rate limit of 10 requests per second.
    """

    def __init__(self, rate: float = 10.0, capacity: float = 10.0) -> None:
        """Initialize the rate limiter.

        Args:
            rate: Token refill rate in tokens per second (default: 10.0).
            capacity: Maximum burst capacity in tokens (default: 10.0).
        """
        if rate <= 0:
            raise ValueError("Rate must be positive")
        if capacity <= 0:
            raise ValueError("Capacity must be positive")

        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> None:
        """Acquire tokens from the bucket, waiting asynchronously if necessary.

        Args:
            tokens: Number of tokens to acquire (default: 1).

        Raises:
            ValueError: If tokens requested is non-positive or exceeds capacity.
        """
        if tokens <= 0:
            raise ValueError("Tokens to acquire must be positive")
        if tokens > self.capacity:
            raise ValueError(
                f"Requested tokens ({tokens}) exceeds capacity ({self.capacity})"
            )

        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self.last_refill
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
                self.last_refill = now

                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return

                wait_time = (tokens - self.tokens) / self.rate
                await asyncio.sleep(wait_time)
