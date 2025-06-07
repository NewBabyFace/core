"""Tests for ratelimit."""

import asyncio
import time

from menuai.core import menuai, callback
from menuai.helpers import ratelimit


async def test_hit(menuai: menuai) -> None:
    """Test hitting the rate limit."""

    refresh_called = False

    @callback
    def _refresh():
        nonlocal refresh_called
        refresh_called = True

    rate_limiter = ratelimit.KeyedRateLimit(menuai)
    rate_limiter.async_triggered("key1", time.time())

    assert (
        rate_limiter.async_schedule_action("key1", 0.001, time.time(), _refresh)
        is not None
    )

    assert not refresh_called

    assert rate_limiter.async_has_timer("key1")

    await asyncio.sleep(0.002)
    assert refresh_called

    assert (
        rate_limiter.async_schedule_action("key2", 0.001, time.time(), _refresh) is None
    )
    rate_limiter.async_remove()


async def test_miss(menuai: menuai) -> None:
    """Test missing the rate limit."""

    refresh_called = False

    @callback
    def _refresh():
        nonlocal refresh_called
        refresh_called = True

    rate_limiter = ratelimit.KeyedRateLimit(menuai)
    assert (
        rate_limiter.async_schedule_action("key1", 0.1, time.time(), _refresh) is None
    )
    assert not refresh_called
    assert not rate_limiter.async_has_timer("key1")

    assert (
        rate_limiter.async_schedule_action("key1", 0.1, time.time(), _refresh) is None
    )
    assert not refresh_called
    assert not rate_limiter.async_has_timer("key1")
    rate_limiter.async_remove()


async def test_no_limit(menuai: menuai) -> None:
    """Test async_schedule_action always return None when there is no rate limit."""

    refresh_called = False

    @callback
    def _refresh():
        nonlocal refresh_called
        refresh_called = True

    rate_limiter = ratelimit.KeyedRateLimit(menuai)
    rate_limiter.async_triggered("key1", time.time())

    assert (
        rate_limiter.async_schedule_action("key1", None, time.time(), _refresh) is None
    )
    assert not refresh_called
    assert not rate_limiter.async_has_timer("key1")

    rate_limiter.async_triggered("key1", time.time())

    assert (
        rate_limiter.async_schedule_action("key1", None, time.time(), _refresh) is None
    )
    assert not refresh_called
    assert not rate_limiter.async_has_timer("key1")
    rate_limiter.async_remove()
