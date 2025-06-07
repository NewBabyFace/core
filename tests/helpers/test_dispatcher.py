"""Test dispatcher helpers."""

from functools import partial

import pytest

from menuai.core import menuai, callback
from menuai.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from menuai.util.signal_type import SignalType, SignalTypeFormat


async def test_simple_function(menuai: menuai) -> None:
    """Test simple function (executor)."""
    calls = []

    def test_funct(data):
        """Test function."""
        calls.append(data)

    async_dispatcher_connect(menuai, "test", test_funct)
    async_dispatcher_send(menuai, "test", 3)
    await menuai.async_block_till_done()

    assert calls == [3]

    async_dispatcher_send(menuai, "test", "bla")
    await menuai.async_block_till_done()

    assert calls == [3, "bla"]


async def test_signal_type(menuai: menuai) -> None:
    """Test dispatcher with SignalType."""
    signal: SignalType[str, int] = SignalType("test")
    calls: list[tuple[str, int]] = []

    def test_funct(data1: str, data2: int) -> None:
        calls.append((data1, data2))

    async_dispatcher_connect(menuai, signal, test_funct)
    async_dispatcher_send(menuai, signal, "Hello", 2)
    await menuai.async_block_till_done()

    assert calls == [("Hello", 2)]

    async_dispatcher_send(menuai, signal, "World", 3)
    await menuai.async_block_till_done()

    assert calls == [("Hello", 2), ("World", 3)]

    # Test compatibility with string keys
    async_dispatcher_send(menuai, "test", "x", 4)
    await menuai.async_block_till_done()

    assert calls == [("Hello", 2), ("World", 3), ("x", 4)]


async def test_signal_type_format(menuai: menuai) -> None:
    """Test dispatcher with SignalType and format."""
    signal: SignalTypeFormat[str, int] = SignalTypeFormat("test-{}")
    calls: list[tuple[str, int]] = []

    def test_funct(data1: str, data2: int) -> None:
        calls.append((data1, data2))

    async_dispatcher_connect(menuai, signal.format("unique-id"), test_funct)
    async_dispatcher_send(menuai, signal.format("unique-id"), "Hello", 2)
    await menuai.async_block_till_done()

    assert calls == [("Hello", 2)]

    # Test compatibility with string keys
    async_dispatcher_send(menuai, "test-unique-id", "x", 4)
    await menuai.async_block_till_done()

    assert calls == [("Hello", 2), ("x", 4)]


async def test_simple_function_unsub(menuai: menuai) -> None:
    """Test simple function (executor) and unsub."""
    calls1 = []
    calls2 = []

    def test_funct1(data):
        """Test function."""
        calls1.append(data)

    def test_funct2(data):
        """Test function."""
        calls2.append(data)

    async_dispatcher_connect(menuai, "test1", test_funct1)
    unsub = async_dispatcher_connect(menuai, "test2", test_funct2)
    async_dispatcher_send(menuai, "test1", 3)
    async_dispatcher_send(menuai, "test2", 4)
    await menuai.async_block_till_done()

    assert calls1 == [3]
    assert calls2 == [4]

    unsub()

    async_dispatcher_send(menuai, "test1", 5)
    async_dispatcher_send(menuai, "test2", 6)
    await menuai.async_block_till_done()

    assert calls1 == [3, 5]
    assert calls2 == [4]

    # check don't kill the flow
    unsub()

    async_dispatcher_send(menuai, "test1", 7)
    async_dispatcher_send(menuai, "test2", 8)
    await menuai.async_block_till_done()

    assert calls1 == [3, 5, 7]
    assert calls2 == [4]


async def test_simple_callback(menuai: menuai) -> None:
    """Test simple callback (async)."""
    calls = []

    @callback
    def test_funct(data):
        """Test function."""
        calls.append(data)

    async_dispatcher_connect(menuai, "test", test_funct)
    async_dispatcher_send(menuai, "test", 3)
    await menuai.async_block_till_done()

    assert calls == [3]

    async_dispatcher_send(menuai, "test", "bla")
    await menuai.async_block_till_done()

    assert calls == [3, "bla"]


async def test_simple_coro(menuai: menuai) -> None:
    """Test simple coro (async)."""
    calls = []

    async def async_test_funct(data):
        """Test function."""
        calls.append(data)

    async_dispatcher_connect(menuai, "test", async_test_funct)
    async_dispatcher_send(menuai, "test", 3)
    await menuai.async_block_till_done()

    assert calls == [3]

    async_dispatcher_send(menuai, "test", "bla")
    await menuai.async_block_till_done()

    assert calls == [3, "bla"]


async def test_simple_function_multiargs(menuai: menuai) -> None:
    """Test simple function (executor)."""
    calls = []

    def test_funct(data1, data2, data3):
        """Test function."""
        calls.append(data1)
        calls.append(data2)
        calls.append(data3)

    async_dispatcher_connect(menuai, "test", test_funct)
    async_dispatcher_send(menuai, "test", 3, 2, "bla")
    await menuai.async_block_till_done()

    assert calls == [3, 2, "bla"]


@pytest.mark.no_fail_on_log_exception
async def test_callback_exception_gets_logged(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test exception raised by signal handler."""

    @callback
    def bad_handler(*args):
        """Record calls."""
        raise Exception("This is a bad message callback")  # noqa: TRY002

    # wrap in partial to test message logging.
    async_dispatcher_connect(menuai, "test", partial(bad_handler))
    async_dispatcher_send(menuai, "test", "bad")

    assert (
        f"Exception in functools.partial({bad_handler}) when dispatching 'test': ('bad',)"
        in caplog.text
    )


@pytest.mark.no_fail_on_log_exception
async def test_coro_exception_gets_logged(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test exception raised by signal handler."""

    async def bad_async_handler(*args):
        """Record calls."""
        raise Exception("This is a bad message in a coro")  # noqa: TRY002

    # wrap in partial to test message logging.
    async_dispatcher_connect(menuai, "test", bad_async_handler)
    async_dispatcher_send(menuai, "test", "bad")
    await menuai.async_block_till_done()

    assert "bad_async_handler" in caplog.text
    assert "when dispatching 'test': ('bad',)" in caplog.text


async def test_dispatcher_add_dispatcher(menuai: menuai) -> None:
    """Test adding a dispatcher from a dispatcher."""
    calls = []

    @callback
    def _new_dispatcher(data):
        calls.append(data)

    @callback
    def _add_new_dispatcher(data):
        calls.append(data)
        async_dispatcher_connect(menuai, "test", _new_dispatcher)

    async_dispatcher_connect(menuai, "test", _add_new_dispatcher)

    async_dispatcher_send(menuai, "test", 3)
    async_dispatcher_send(menuai, "test", 4)
    async_dispatcher_send(menuai, "test", 5)

    assert calls == [3, 4, 4, 5, 5]


async def test_thread_safety_checks(menuai: menuai) -> None:
    """Test dispatcher thread safety checks."""
    calls = []

    @callback
    def _dispatcher(data):
        calls.append(data)

    async_dispatcher_connect(menuai, "test", _dispatcher)

    with pytest.raises(
        RuntimeError,
        match="Detected code that calls async_dispatcher_send from a thread.",
    ):
        await menuai.async_add_executor_job(async_dispatcher_send, menuai, "test", 3)

    async_dispatcher_send(menuai, "test", 4)
    assert calls == [4]
