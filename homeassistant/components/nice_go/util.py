"""Utilities for Nice G.O."""

from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any, Protocol, runtime_checkable

from aiohttp import ClientError
from nice_go import ApiError, AuthFailedError

from menuai.exceptions import ConfigEntryAuthFailed, menuaiError
from menuai.helpers.update_coordinator import UpdateFailed

from .const import DOMAIN


@runtime_checkable
class _ArgsProtocol(Protocol):
    coordinator: Any
    menuai: Any


def retry[_R, **P](
    translation_key: str,
) -> Callable[
    [Callable[P, Coroutine[Any, Any, _R]]], Callable[P, Coroutine[Any, Any, _R]]
]:
    """Retry decorator to handle API errors."""

    def decorator(
        func: Callable[P, Coroutine[Any, Any, _R]],
    ) -> Callable[P, Coroutine[Any, Any, _R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs):
            instance = args[0]
            if not isinstance(instance, _ArgsProtocol):
                raise TypeError("First argument must have correct attributes")
            try:
                return await func(*args, **kwargs)
            except (ApiError, ClientError) as err:
                raise menuaiError(
                    translation_domain=DOMAIN,
                    translation_key=translation_key,
                    translation_placeholders={"exception": str(err)},
                ) from err
            except AuthFailedError:
                # Try refreshing token and retry
                try:
                    await instance.coordinator.update_refresh_token()
                    return await func(*args, **kwargs)
                except (ApiError, ClientError, UpdateFailed) as err:
                    raise menuaiError(
                        translation_domain=DOMAIN,
                        translation_key=translation_key,
                        translation_placeholders={"exception": str(err)},
                    ) from err
                except (AuthFailedError, ConfigEntryAuthFailed) as err:
                    instance.coordinator.config_entry.async_start_reauth(instance.menuai)
                    raise menuaiError(
                        translation_domain=DOMAIN,
                        translation_key=translation_key,
                        translation_placeholders={"exception": str(err)},
                    ) from err

        return wrapper

    return decorator
