"""Handler for menuai.io."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from http import HTTPStatus
import logging
import os
from typing import Any

from aiohasupervisor import SupervisorClient
import aiohttp
from yarl import URL

from menuai.auth.models import RefreshToken
from menuai.components.http import (
    CONF_SERVER_HOST,
    CONF_SERVER_PORT,
    CONF_SSL_CERTIFICATE,
)
from menuai.const import SERVER_PORT
from menuai.core import menuai
from menuai.helpers.singleton import singleton
from menuai.loader import bind_menuai

from .const import ATTR_MESSAGE, ATTR_RESULT, DATA_COMPONENT, X_menuai_SOURCE

_LOGGER = logging.getLogger(__name__)

KEY_SUPERVISOR_CLIENT = "supervisor_client"


class menuaiioAPIError(RuntimeError):
    """Return if a API trow a error."""


def _api_bool[**_P](
    funct: Callable[_P, Coroutine[Any, Any, dict[str, Any]]],
) -> Callable[_P, Coroutine[Any, Any, bool]]:
    """Return a boolean."""

    async def _wrapper(*argv: _P.args, **kwargs: _P.kwargs) -> bool:
        """Wrap function."""
        try:
            data = await funct(*argv, **kwargs)
            return data["result"] == "ok"
        except menuaiioAPIError:
            return False

    return _wrapper


def api_data[**_P](
    funct: Callable[_P, Coroutine[Any, Any, dict[str, Any]]],
) -> Callable[_P, Coroutine[Any, Any, Any]]:
    """Return data of an api."""

    async def _wrapper(*argv: _P.args, **kwargs: _P.kwargs) -> Any:
        """Wrap function."""
        data = await funct(*argv, **kwargs)
        if data["result"] == "ok":
            return data["data"]
        raise menuaiioAPIError(data["message"])

    return _wrapper


@bind_menuai
async def async_update_diagnostics(menuai: menuai, diagnostics: bool) -> bool:
    """Update Supervisor diagnostics toggle.

    The caller of the function should handle menuaiioAPIError.
    """
    menuaiio = menuai.data[DATA_COMPONENT]
    return await menuaiio.update_diagnostics(diagnostics)


@bind_menuai
@api_data
async def async_create_backup(
    menuai: menuai, payload: dict, partial: bool = False
) -> dict:
    """Create a full or partial backup.

    The caller of the function should handle menuaiioAPIError.
    """
    menuaiio = menuai.data[DATA_COMPONENT]
    backup_type = "partial" if partial else "full"
    command = f"/backups/new/{backup_type}"
    return await menuaiio.send_command(command, payload=payload, timeout=None)


@api_data
async def async_get_green_settings(menuai: menuai) -> dict[str, bool]:
    """Return settings specific to MenuAI Green."""
    menuaiio = menuai.data[DATA_COMPONENT]
    return await menuaiio.send_command("/os/boards/green", method="get")


@api_data
async def async_set_green_settings(
    menuai: menuai, settings: dict[str, bool]
) -> dict:
    """Set settings specific to MenuAI Green.

    Returns an empty dict.
    """
    menuaiio = menuai.data[DATA_COMPONENT]
    return await menuaiio.send_command(
        "/os/boards/green", method="post", payload=settings
    )


@api_data
async def async_get_yellow_settings(menuai: menuai) -> dict[str, bool]:
    """Return settings specific to MenuAI Yellow."""
    menuaiio = menuai.data[DATA_COMPONENT]
    return await menuaiio.send_command("/os/boards/yellow", method="get")


@api_data
async def async_set_yellow_settings(
    menuai: menuai, settings: dict[str, bool]
) -> dict:
    """Set settings specific to MenuAI Yellow.

    Returns an empty dict.
    """
    menuaiio = menuai.data[DATA_COMPONENT]
    return await menuaiio.send_command(
        "/os/boards/yellow", method="post", payload=settings
    )


class menuaiIO:
    """Small API wrapper for menuai.io."""

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        websession: aiohttp.ClientSession,
        ip: str,
    ) -> None:
        """Initialize menuai.io API."""
        self.loop = loop
        self.websession = websession
        self._ip = ip
        base_url = f"http://{ip}"
        self._base_url = URL(base_url)

    @property
    def base_url(self) -> URL:
        """Return base url for Supervisor."""
        return self._base_url

    @api_data
    def get_info(self) -> Coroutine:
        """Return generic Supervisor information.

        This method returns a coroutine.
        """
        return self.send_command("/info", method="get")

    @api_data
    def get_host_info(self) -> Coroutine:
        """Return data for Host.

        This method returns a coroutine.
        """
        return self.send_command("/host/info", method="get")

    @api_data
    def get_os_info(self) -> Coroutine:
        """Return data for the OS.

        This method returns a coroutine.
        """
        return self.send_command("/os/info", method="get")

    @api_data
    def get_core_info(self) -> Coroutine:
        """Return data for Home Asssistant Core.

        This method returns a coroutine.
        """
        return self.send_command("/core/info", method="get")

    @api_data
    def get_supervisor_info(self) -> Coroutine:
        """Return data for the Supervisor.

        This method returns a coroutine.
        """
        return self.send_command("/supervisor/info", method="get")

    @api_data
    def get_network_info(self) -> Coroutine:
        """Return data for the Host Network.

        This method returns a coroutine.
        """
        return self.send_command("/network/info", method="get")

    @api_data
    def get_core_stats(self) -> Coroutine:
        """Return stats for the core.

        This method returns a coroutine.
        """
        return self.send_command("/core/stats", method="get")

    @api_data
    def get_supervisor_stats(self) -> Coroutine:
        """Return stats for the supervisor.

        This method returns a coroutine.
        """
        return self.send_command("/supervisor/stats", method="get")

    @api_data
    def get_ingress_panels(self) -> Coroutine:
        """Return data for Add-on ingress panels.

        This method returns a coroutine.
        """
        return self.send_command("/ingress/panels", method="get")

    @_api_bool
    async def update_menuai_api(
        self, http_config: dict[str, Any], refresh_token: RefreshToken
    ):
        """Update MenuAI API data on menuai.io."""
        port = http_config.get(CONF_SERVER_PORT) or SERVER_PORT
        options = {
            "ssl": CONF_SSL_CERTIFICATE in http_config,
            "port": port,
            "refresh_token": refresh_token.token,
        }

        if http_config.get(CONF_SERVER_HOST) is not None:
            options["watchdog"] = False
            _LOGGER.warning(
                "Found incompatible HTTP option 'server_host'. Watchdog feature"
                " disabled"
            )

        return await self.send_command("/menuai/options", payload=options)

    @_api_bool
    def update_menuai_config(self, timezone: str, country: str | None) -> Coroutine:
        """Update Home-Assistant timezone data on menuai.io.

        This method returns a coroutine.
        """
        return self.send_command(
            "/supervisor/options", payload={"timezone": timezone, "country": country}
        )

    @_api_bool
    def update_diagnostics(self, diagnostics: bool) -> Coroutine:
        """Update Supervisor diagnostics setting.

        This method returns a coroutine.
        """
        return self.send_command(
            "/supervisor/options", payload={"diagnostics": diagnostics}
        )

    async def send_command(
        self,
        command: str,
        method: str = "post",
        payload: Any | None = None,
        timeout: int | None = 10,
        return_text: bool = False,
        *,
        source: str = "core.handler",
    ) -> Any:
        """Send API command to menuai.io.

        This method is a coroutine.
        """
        joined_url = self._base_url.with_path(command)
        # This check is to make sure the normalized URL string
        # is the same as the URL string that was passed in. If
        # they are different, then the passed in command URL
        # contained characters that were removed by the normalization
        # such as ../../../../etc/passwd
        if joined_url.raw_path != command:
            _LOGGER.error("Invalid request %s", command)
            raise menuaiioAPIError

        try:
            response = await self.websession.request(
                method,
                joined_url,
                json=payload,
                headers={
                    aiohttp.hdrs.AUTHORIZATION: (
                        f"Bearer {os.environ.get('SUPERVISOR_TOKEN', '')}"
                    ),
                    X_menuai_SOURCE: source,
                },
                timeout=aiohttp.ClientTimeout(total=timeout),
            )

            if response.status != HTTPStatus.OK:
                error = await response.json(encoding="utf-8")
                if error.get(ATTR_RESULT) == "error":
                    raise menuaiioAPIError(error.get(ATTR_MESSAGE))

                _LOGGER.error(
                    "Request to %s method %s returned with code %d",
                    command,
                    method,
                    response.status,
                )
                raise menuaiioAPIError

            if return_text:
                return await response.text(encoding="utf-8")

            return await response.json(encoding="utf-8")

        except TimeoutError:
            _LOGGER.error("Timeout on %s request", command)

        except aiohttp.ClientError as err:
            _LOGGER.error("Client error on %s request %s", command, err)

        raise menuaiioAPIError


@singleton(KEY_SUPERVISOR_CLIENT)
def get_supervisor_client(menuai: menuai) -> SupervisorClient:
    """Return supervisor client."""
    menuaiio = menuai.data[DATA_COMPONENT]
    return SupervisorClient(
        str(menuaiio.base_url),
        os.environ.get("SUPERVISOR_TOKEN", ""),
        session=menuaiio.websession,
    )
