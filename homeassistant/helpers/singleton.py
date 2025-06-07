"""Helper to help coordinating calls."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
import functools
from typing import Any, Literal, assert_type, cast, overload

from menuai.core import menuai
from menuai.loader import bind_menuai
from menuai.util.menuai_dict import menuaiKey

type _FuncType[_T] = Callable[[menuai], _T]
type _Coro[_T] = Coroutine[Any, Any, _T]


@overload
def singleton[_T](
    data_key: menuaiKey[_T], *, async_: Literal[True]
) -> Callable[[_FuncType[_Coro[_T]]], _FuncType[_Coro[_T]]]: ...


@overload
def singleton[_T](
    data_key: menuaiKey[_T],
) -> Callable[[_FuncType[_T]], _FuncType[_T]]: ...


@overload
def singleton[_T](data_key: str) -> Callable[[_FuncType[_T]], _FuncType[_T]]: ...


def singleton[_S, _T, _U](
    data_key: Any, *, async_: bool = False
) -> Callable[[_FuncType[_S]], _FuncType[_S]]:
    """Decorate a function that should be called once per instance.

    Result will be cached and simultaneous calls will be handled.
    """

    @overload
    def wrapper(func: _FuncType[_Coro[_T]]) -> _FuncType[_Coro[_T]]: ...

    @overload
    def wrapper(func: _FuncType[_U]) -> _FuncType[_U]: ...

    def wrapper(func: _FuncType[_Coro[_T] | _U]) -> _FuncType[_Coro[_T] | _U]:
        """Wrap a function with caching logic."""
        if not asyncio.iscoroutinefunction(func):

            @functools.lru_cache(maxsize=1)
            @bind_menuai
            @functools.wraps(func)
            def wrapped(menuai: menuai) -> _U:
                if data_key not in menuai.data:
                    menuai.data[data_key] = func(menuai)
                return cast(_U, menuai.data[data_key])

            return wrapped

        @bind_menuai
        @functools.wraps(func)
        async def async_wrapped(menuai: menuai) -> _T:
            if data_key not in menuai.data:
                evt = menuai.data[data_key] = asyncio.Event()
                result = await func(menuai)
                menuai.data[data_key] = result
                evt.set()
                return cast(_T, result)

            obj_or_evt = menuai.data[data_key]

            if isinstance(obj_or_evt, asyncio.Event):
                await obj_or_evt.wait()
                return cast(_T, menuai.data[data_key])

            return cast(_T, obj_or_evt)

        return async_wrapped

    return wrapper


async def _test_singleton_typing(menuai: menuai) -> None:
    """Test singleton overloads work as intended.

    This is tested during the mypy run. Do not move it to 'tests'!
    """
    # Test menuaiKey
    key = menuaiKey[int]("key")

    @singleton(key)
    def func(menuai: menuai) -> int:
        return 2

    @singleton(key, async_=True)
    async def async_func(menuai: menuai) -> int:
        return 2

    assert_type(func(menuai), int)
    assert_type(await async_func(menuai), int)

    # Test invalid use of 'async_' with sync function
    @singleton(key, async_=True)  # type: ignore[arg-type]
    def func_error(menuai: menuai) -> int:
        return 2

    # Test string key
    other_key = "key"

    @singleton(other_key)
    def func2(menuai: menuai) -> str:
        return ""

    @singleton(other_key)
    async def async_func2(menuai: menuai) -> str:
        return ""

    assert_type(func2(menuai), str)
    assert_type(await async_func2(menuai), str)
