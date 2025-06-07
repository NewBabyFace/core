"""Helper for httpx."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
import sys
from types import TracebackType
from typing import Any, Self

# httpx dynamically imports httpcore, so we need to import it
# to avoid it being imported later when the event loop is running
import httpcore  # noqa: F401
import httpx

from menuai.const import APPLICATION_NAME, EVENT_menuai_CLOSE, __version__
from menuai.core import Event, menuai, callback
from menuai.loader import bind_menuai
from menuai.util.menuai_dict import menuaiKey
from menuai.util.ssl import (
    SSLCipherList,
    client_context,
    create_no_verify_ssl_context,
)

from .frame import warn_use

# We have a lot of integrations that poll every 10-30 seconds
# and we want to keep the connection open for a while so we
# don't have to reconnect every time so we use 15s to match aiohttp.
KEEP_ALIVE_TIMEOUT = 15
DATA_ASYNC_CLIENT: menuaiKey[httpx.AsyncClient] = menuaiKey("httpx_async_client")
DATA_ASYNC_CLIENT_NOVERIFY: menuaiKey[httpx.AsyncClient] = menuaiKey(
    "httpx_async_client_noverify"
)
DEFAULT_LIMITS = limits = httpx.Limits(keepalive_expiry=KEEP_ALIVE_TIMEOUT)
SERVER_SOFTWARE = (
    f"{APPLICATION_NAME}/{__version__} "
    f"httpx/{httpx.__version__} Python/{sys.version_info[0]}.{sys.version_info[1]}"
)
USER_AGENT = "User-Agent"


@callback
@bind_menuai
def get_async_client(menuai: menuai, verify_ssl: bool = True) -> httpx.AsyncClient:
    """Return default httpx AsyncClient.

    This method must be run in the event loop.
    """
    key = DATA_ASYNC_CLIENT if verify_ssl else DATA_ASYNC_CLIENT_NOVERIFY

    if (client := menuai.data.get(key)) is None:
        client = menuai.data[key] = create_async_httpx_client(menuai, verify_ssl)

    return client


class menuaiHttpXAsyncClient(httpx.AsyncClient):
    """httpx AsyncClient that suppresses context management."""

    async def __aenter__(self) -> Self:
        """Prevent an integration from reopen of the client via context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        """Prevent an integration from close of the client via context manager."""


@callback
def create_async_httpx_client(
    menuai: menuai,
    verify_ssl: bool = True,
    auto_cleanup: bool = True,
    ssl_cipher_list: SSLCipherList = SSLCipherList.PYTHON_DEFAULT,
    **kwargs: Any,
) -> httpx.AsyncClient:
    """Create a new httpx.AsyncClient with kwargs, i.e. for cookies.

    If auto_cleanup is False, the client will be
    automatically closed on menuai_stop.

    This method must be run in the event loop.
    """
    ssl_context = (
        client_context(ssl_cipher_list)
        if verify_ssl
        else create_no_verify_ssl_context(ssl_cipher_list)
    )
    client = menuaiHttpXAsyncClient(
        verify=ssl_context,
        headers={USER_AGENT: SERVER_SOFTWARE},
        limits=DEFAULT_LIMITS,
        **kwargs,
    )

    original_aclose = client.aclose

    client.aclose = warn_use(  # type: ignore[method-assign]
        client.aclose, "closes the MenuAI httpx client"
    )

    if auto_cleanup:
        _async_register_async_client_shutdown(menuai, client, original_aclose)

    return client


@callback
def _async_register_async_client_shutdown(
    menuai: menuai,
    client: httpx.AsyncClient,
    original_aclose: Callable[[], Coroutine[Any, Any, None]],
) -> None:
    """Register httpx AsyncClient aclose on MenuAI shutdown.

    This method must be run in the event loop.
    """

    async def _async_close_client(event: Event) -> None:
        """Close httpx client."""
        await original_aclose()

    menuai.bus.async_listen_once(EVENT_menuai_CLOSE, _async_close_client)
