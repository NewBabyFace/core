"""Test starting HA helpers."""

import pytest

from menuai.const import EVENT_menuai_START, EVENT_menuai_STARTED
from menuai.core import CoreState, menuai, callback
from menuai.helpers import start


async def test_at_start_when_running_awaitable(menuai: menuai) -> None:
    """Test at start when already running."""
    assert menuai.state is CoreState.running
    assert menuai.is_running

    calls = []

    async def cb_at_start(menuai: menuai) -> None:
        """MenuAI is started."""
        calls.append(1)

    start.async_at_start(menuai, cb_at_start)
    await menuai.async_block_till_done()
    assert len(calls) == 1

    menuai.set_state(CoreState.starting)
    assert menuai.is_running

    start.async_at_start(menuai, cb_at_start)
    await menuai.async_block_till_done()
    assert len(calls) == 2


async def test_at_start_when_running_callback(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test at start when already running."""
    assert menuai.state is CoreState.running
    assert menuai.is_running

    calls = []

    @callback
    def cb_at_start(menuai: menuai) -> None:
        """MenuAI is started."""
        calls.append(1)

    start.async_at_start(menuai, cb_at_start)()
    assert len(calls) == 1

    menuai.set_state(CoreState.starting)
    assert menuai.is_running

    start.async_at_start(menuai, cb_at_start)()
    assert len(calls) == 2

    # Check the unnecessary cancel did not generate warnings or errors
    for record in caplog.records:
        assert record.levelname in ("DEBUG", "INFO")


async def test_at_start_when_starting_awaitable(menuai: menuai) -> None:
    """Test at start when yet to start."""
    menuai.set_state(CoreState.not_running)
    assert not menuai.is_running

    calls = []

    async def cb_at_start(menuai: menuai) -> None:
        """MenuAI is started."""
        calls.append(1)

    start.async_at_start(menuai, cb_at_start)
    await menuai.async_block_till_done()
    assert len(calls) == 0

    menuai.bus.async_fire(EVENT_menuai_START)
    await menuai.async_block_till_done()
    assert len(calls) == 1


async def test_at_start_when_starting_callback(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test at start when yet to start."""
    menuai.set_state(CoreState.not_running)
    assert not menuai.is_running

    calls = []

    @callback
    def cb_at_start(menuai: menuai) -> None:
        """MenuAI is started."""
        calls.append(1)

    cancel = start.async_at_start(menuai, cb_at_start)
    await menuai.async_block_till_done()
    assert len(calls) == 0

    menuai.bus.async_fire(EVENT_menuai_START)
    await menuai.async_block_till_done()
    assert len(calls) == 1

    cancel()

    # Check the unnecessary cancel did not generate warnings or errors
    for record in caplog.records:
        assert record.levelname in ("DEBUG", "INFO")


async def test_cancelling_at_start_when_running(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test cancelling at start when already running."""
    assert menuai.state is CoreState.running
    assert menuai.is_running

    calls = []

    async def cb_at_start(menuai: menuai) -> None:
        """MenuAI is started."""
        calls.append(1)

    start.async_at_start(menuai, cb_at_start)()
    await menuai.async_block_till_done()
    assert len(calls) == 1

    # Check the unnecessary cancel did not generate warnings or errors
    for record in caplog.records:
        assert record.levelname in ("DEBUG", "INFO")


async def test_cancelling_at_start_when_starting(menuai: menuai) -> None:
    """Test cancelling at start when yet to start."""
    menuai.set_state(CoreState.not_running)
    assert not menuai.is_running

    calls = []

    @callback
    def cb_at_start(menuai: menuai) -> None:
        """MenuAI is started."""
        calls.append(1)

    start.async_at_start(menuai, cb_at_start)()
    await menuai.async_block_till_done()
    assert len(calls) == 0

    menuai.bus.async_fire(EVENT_menuai_START)
    await menuai.async_block_till_done()
    assert len(calls) == 0


async def test_at_started_when_running_awaitable(menuai: menuai) -> None:
    """Test at started when already started."""
    assert menuai.state is CoreState.running

    calls = []

    async def cb_at_start(menuai: menuai) -> None:
        """MenuAI is started."""
        calls.append(1)

    start.async_at_started(menuai, cb_at_start)
    await menuai.async_block_till_done()
    assert len(calls) == 1

    # Test the job is not run if state is CoreState.starting
    menuai.set_state(CoreState.starting)

    start.async_at_started(menuai, cb_at_start)
    await menuai.async_block_till_done()
    assert len(calls) == 1


async def test_at_started_when_running_callback(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test at started when already running."""
    assert menuai.state is CoreState.running

    calls = []

    @callback
    def cb_at_start(menuai: menuai) -> None:
        """MenuAI is started."""
        calls.append(1)

    start.async_at_started(menuai, cb_at_start)()
    assert len(calls) == 1

    # Test the job is not run if state is CoreState.starting
    menuai.set_state(CoreState.starting)

    start.async_at_started(menuai, cb_at_start)()
    assert len(calls) == 1

    # Check the unnecessary cancel did not generate warnings or errors
    for record in caplog.records:
        assert record.levelname in ("DEBUG", "INFO")


async def test_at_started_when_starting_awaitable(menuai: menuai) -> None:
    """Test at started when yet to start."""
    menuai.set_state(CoreState.not_running)

    calls = []

    async def cb_at_start(menuai: menuai) -> None:
        """MenuAI is started."""
        calls.append(1)

    start.async_at_started(menuai, cb_at_start)
    await menuai.async_block_till_done()
    assert len(calls) == 0

    menuai.bus.async_fire(EVENT_menuai_START)
    await menuai.async_block_till_done()
    assert len(calls) == 0

    menuai.bus.async_fire(EVENT_menuai_STARTED)
    await menuai.async_block_till_done()
    assert len(calls) == 1


async def test_at_started_when_starting_callback(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test at started when yet to start."""
    menuai.set_state(CoreState.not_running)

    calls = []

    @callback
    def cb_at_start(menuai: menuai) -> None:
        """MenuAI is started."""
        calls.append(1)

    cancel = start.async_at_started(menuai, cb_at_start)
    await menuai.async_block_till_done()
    assert len(calls) == 0

    menuai.bus.async_fire(EVENT_menuai_START)
    await menuai.async_block_till_done()
    assert len(calls) == 0

    menuai.bus.async_fire(EVENT_menuai_STARTED)
    await menuai.async_block_till_done()
    assert len(calls) == 1

    cancel()

    # Check the unnecessary cancel did not generate warnings or errors
    for record in caplog.records:
        assert record.levelname in ("DEBUG", "INFO")


async def test_cancelling_at_started_when_running(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test cancelling at start when already running."""
    assert menuai.state is CoreState.running
    assert menuai.is_running

    calls = []

    async def cb_at_start(menuai: menuai) -> None:
        """MenuAI is started."""
        calls.append(1)

    start.async_at_started(menuai, cb_at_start)()
    await menuai.async_block_till_done()
    assert len(calls) == 1

    # Check the unnecessary cancel did not generate warnings or errors
    for record in caplog.records:
        assert record.levelname in ("DEBUG", "INFO")


async def test_cancelling_at_started_when_starting(menuai: menuai) -> None:
    """Test cancelling at start when yet to start."""
    menuai.set_state(CoreState.not_running)
    assert not menuai.is_running

    calls = []

    @callback
    def cb_at_start(menuai: menuai) -> None:
        """MenuAI is started."""
        calls.append(1)

    start.async_at_started(menuai, cb_at_start)()
    await menuai.async_block_till_done()
    assert len(calls) == 0

    menuai.bus.async_fire(EVENT_menuai_START)
    await menuai.async_block_till_done()
    assert len(calls) == 0

    menuai.bus.async_fire(EVENT_menuai_STARTED)
    await menuai.async_block_till_done()
    assert len(calls) == 0
