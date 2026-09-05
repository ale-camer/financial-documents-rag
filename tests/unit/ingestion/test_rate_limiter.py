"""Unit tests for AsyncTokenBucket rate limiter."""

import asyncio
import time

import pytest

from src.ingestion.rate_limiter import AsyncTokenBucket


@pytest.mark.asyncio
async def test_initial_burst() -> None:
    """Verify that the first 10 tokens are acquired immediately without delay."""
    bucket = AsyncTokenBucket(rate=10.0, capacity=10.0)

    start = time.monotonic()
    for _ in range(10):
        await bucket.acquire(1)
    duration = time.monotonic() - start

    assert duration < 0.05


@pytest.mark.asyncio
async def test_throttling() -> None:
    """Verify that the 11th token wait is approximately 100ms."""
    bucket = AsyncTokenBucket(rate=10.0, capacity=10.0)

    for _ in range(10):
        await bucket.acquire(1)

    start = time.monotonic()
    await bucket.acquire(1)
    duration = time.monotonic() - start

    assert duration >= 0.08


@pytest.mark.asyncio
async def test_refill_over_time() -> None:
    """Verify that after sleeping 0.5s, 5 tokens are replenished."""
    bucket = AsyncTokenBucket(rate=10.0, capacity=10.0)

    for _ in range(10):
        await bucket.acquire(1)

    await asyncio.sleep(0.5)

    start = time.monotonic()
    for _ in range(5):
        await bucket.acquire(1)
    duration = time.monotonic() - start

    assert duration < 0.05


@pytest.mark.asyncio
async def test_concurrency() -> None:
    """Verify that asyncio.gather with 15 tasks respects the 10 req/s rate."""
    bucket = AsyncTokenBucket(rate=10.0, capacity=10.0)

    start = time.monotonic()
    tasks = [asyncio.create_task(bucket.acquire(1)) for _ in range(15)]
    await asyncio.gather(*tasks)
    duration = time.monotonic() - start

    # 10 immediate + 5 delayed by 0.1s each -> ~0.5s
    assert duration >= 0.40


def test_invalid_parameters() -> None:
    """Verify validation of bucket parameters."""
    with pytest.raises(ValueError, match="Rate must be positive"):
        AsyncTokenBucket(rate=0)

    with pytest.raises(ValueError, match="Capacity must be positive"):
        AsyncTokenBucket(capacity=-1)


@pytest.mark.asyncio
async def test_invalid_acquire() -> None:
    """Verify validation when acquiring tokens."""
    bucket = AsyncTokenBucket(rate=10.0, capacity=10.0)

    with pytest.raises(ValueError, match="Tokens to acquire must be positive"):
        await bucket.acquire(0)

    with pytest.raises(ValueError, match="exceeds capacity"):
        await bucket.acquire(15)
