"""The Diagnostics integration."""

from __future__ import annotations

from collections.abc import Callable, Coroutine, Mapping
from dataclasses import dataclass, field
from http import HTTPStatus
import json
import logging
from typing import Any, Protocol

from aiohttp import web
import voluptuous as vol

from menuai.components import http, websocket_api
from menuai.config_entries import ConfigEntry
from menuai.core import menuai, callback
from menuai.helpers import (
    config_validation as cv,
    device_registry as dr,
    integration_platform,
)
from menuai.helpers.device_registry import DeviceEntry
from menuai.helpers.json import (
    ExtendedJSONEncoder,
    find_paths_unserializable_data,
)
from menuai.helpers.system_info import async_get_system_info
from menuai.helpers.typing import ConfigType
from menuai.loader import (
    Manifest,
    async_get_custom_components,
    async_get_integration,
)
from menuai.setup import async_get_domain_setup_times
from menuai.util.menuai_dict import menuaiKey
from menuai.util.json import format_unserializable_data

from .const import DOMAIN, REDACTED, DiagnosticsSubType, DiagnosticsType
from .util import async_redact_data

__all__ = ["REDACTED", "async_redact_data"]

_LOGGER = logging.getLogger(__name__)


CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)
_DIAGNOSTICS_DATA: menuaiKey[DiagnosticsData] = menuaiKey(DOMAIN)


@dataclass(slots=True)
class DiagnosticsPlatformData:
    """Diagnostic platform data."""

    config_entry_diagnostics: (
        Callable[[menuai, ConfigEntry], Coroutine[Any, Any, Mapping[str, Any]]]
        | None
    )
    device_diagnostics: (
        Callable[
            [menuai, ConfigEntry, DeviceEntry],
            Coroutine[Any, Any, Mapping[str, Any]],
        ]
        | None
    )


@dataclass(slots=True)
class DiagnosticsData:
    """Diagnostic data."""

    platforms: dict[str, DiagnosticsPlatformData] = field(default_factory=dict)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up Diagnostics from a config entry."""
    menuai.data[_DIAGNOSTICS_DATA] = DiagnosticsData()

    await integration_platform.async_process_integration_platforms(
        menuai, DOMAIN, _register_diagnostics_platform
    )

    websocket_api.async_register_command(menuai, handle_info)
    websocket_api.async_register_command(menuai, handle_get)
    menuai.http.register_view(DownloadDiagnosticsView)

    return True


class DiagnosticsProtocol(Protocol):
    """Define the format that diagnostics platforms can have."""

    async def async_get_config_entry_diagnostics(
        self, menuai: menuai, config_entry: ConfigEntry
    ) -> Mapping[str, Any]:
        """Return diagnostics for a config entry."""

    async def async_get_device_diagnostics(
        self, menuai: menuai, config_entry: ConfigEntry, device: DeviceEntry
    ) -> Mapping[str, Any]:
        """Return diagnostics for a device."""


@callback
def _register_diagnostics_platform(
    menuai: menuai, integration_domain: str, platform: DiagnosticsProtocol
) -> None:
    """Register a diagnostics platform."""
    diagnostics_data = menuai.data[_DIAGNOSTICS_DATA]
    diagnostics_data.platforms[integration_domain] = DiagnosticsPlatformData(
        getattr(platform, "async_get_config_entry_diagnostics", None),
        getattr(platform, "async_get_device_diagnostics", None),
    )


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): "diagnostics/list"})
@callback
def handle_info(
    menuai: menuai, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """List all possible diagnostic handlers."""
    diagnostics_data = menuai.data[_DIAGNOSTICS_DATA]
    result = [
        {
            "domain": domain,
            "handlers": {
                DiagnosticsType.CONFIG_ENTRY: info.config_entry_diagnostics is not None,
                DiagnosticsSubType.DEVICE: info.device_diagnostics is not None,
            },
        }
        for domain, info in diagnostics_data.platforms.items()
    ]
    connection.send_result(msg["id"], result)


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "diagnostics/get",
        vol.Required("domain"): str,
    }
)
@callback
def handle_get(
    menuai: menuai, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """List all diagnostic handlers for a domain."""
    domain = msg["domain"]
    diagnostics_data = menuai.data[_DIAGNOSTICS_DATA]

    if (info := diagnostics_data.platforms.get(domain)) is None:
        connection.send_error(
            msg["id"], websocket_api.ERR_NOT_FOUND, "Domain not supported"
        )
        return

    connection.send_result(
        msg["id"],
        {
            "domain": domain,
            "handlers": {
                DiagnosticsType.CONFIG_ENTRY: info.config_entry_diagnostics is not None,
                DiagnosticsSubType.DEVICE: info.device_diagnostics is not None,
            },
        },
    )


@callback
def async_format_manifest(manifest: Manifest) -> Manifest:
    """Format manifest for diagnostics.

    Remove the @ from codeowners so that
    when users download the diagnostics and paste
    the codeowners into the repository, it will
    not notify the users in the codeowners file.
    """
    manifest_copy = manifest.copy()
    if "codeowners" in manifest_copy:
        manifest_copy["codeowners"] = [
            codeowner.lstrip("@") for codeowner in manifest_copy["codeowners"]
        ]
    return manifest_copy


async def _async_get_json_file_response(
    menuai: menuai,
    data: Mapping[str, Any],
    filename: str,
    domain: str,
    d_id: str,
    sub_id: str | None = None,
) -> web.Response:
    """Return JSON file from dictionary."""
    menuai_sys_info = await async_get_system_info(menuai)
    menuai_sys_info["run_as_root"] = menuai_sys_info["user"] == "root"
    del menuai_sys_info["user"]

    integration = await async_get_integration(menuai, domain)
    custom_components = {}
    all_custom_components = await async_get_custom_components(menuai)
    for cc_domain, cc_obj in all_custom_components.items():
        custom_components[cc_domain] = {
            "documentation": cc_obj.documentation,
            "version": cc_obj.version,
            "requirements": cc_obj.requirements,
        }
    payload = {
        "home_assistant": menuai_sys_info,
        "custom_components": custom_components,
        "integration_manifest": async_format_manifest(integration.manifest),
        "setup_times": async_get_domain_setup_times(menuai, domain),
        "data": data,
    }
    try:
        json_data = json.dumps(payload, indent=2, cls=ExtendedJSONEncoder)
    except TypeError:
        _LOGGER.error(
            "Failed to serialize to JSON: %s/%s%s. Bad data at %s",
            DiagnosticsType.CONFIG_ENTRY.value,
            d_id,
            f"/{DiagnosticsSubType.DEVICE.value}/{sub_id}"
            if sub_id is not None
            else "",
            format_unserializable_data(find_paths_unserializable_data(payload)),
        )
        return web.Response(status=HTTPStatus.INTERNAL_SERVER_ERROR)

    return web.Response(
        body=json_data,
        content_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}.json"'},
    )


class DownloadDiagnosticsView(http.menuaiView):
    """Download diagnostics view."""

    url = "/api/diagnostics/{d_type}/{d_id}"
    extra_urls = ["/api/diagnostics/{d_type}/{d_id}/{sub_type}/{sub_id}"]
    name = "api:diagnostics"

    async def get(
        self,
        request: web.Request,
        d_type: str,
        d_id: str,
        sub_type: str | None = None,
        sub_id: str | None = None,
    ) -> web.Response:
        """Download diagnostics."""
        # Validate d_type and sub_type
        try:
            DiagnosticsType(d_type)
        except ValueError:
            return web.Response(status=HTTPStatus.BAD_REQUEST)

        if sub_type is not None:
            try:
                DiagnosticsSubType(sub_type)
            except ValueError:
                return web.Response(status=HTTPStatus.BAD_REQUEST)

        device_diagnostics = sub_type is not None

        menuai = request.app[http.KEY_menuai]

        if (config_entry := menuai.config_entries.async_get_entry(d_id)) is None:
            return web.Response(status=HTTPStatus.NOT_FOUND)

        diagnostics_data = menuai.data[_DIAGNOSTICS_DATA]
        if (info := diagnostics_data.platforms.get(config_entry.domain)) is None:
            return web.Response(status=HTTPStatus.NOT_FOUND)

        filename = f"{config_entry.domain}-{config_entry.entry_id}"

        if not device_diagnostics:
            # Config entry diagnostics
            if info.config_entry_diagnostics is None:
                return web.Response(status=HTTPStatus.NOT_FOUND)
            data = await info.config_entry_diagnostics(menuai, config_entry)
            filename = f"{DiagnosticsType.CONFIG_ENTRY}-{filename}"
            return await _async_get_json_file_response(
                menuai, data, filename, config_entry.domain, d_id
            )

        # Device diagnostics
        dev_reg = dr.async_get(menuai)
        if sub_id is None:
            return web.Response(status=HTTPStatus.BAD_REQUEST)

        if (device := dev_reg.async_get(sub_id)) is None:
            return web.Response(status=HTTPStatus.NOT_FOUND)

        filename += f"-{device.name}-{device.id}"

        if info.device_diagnostics is None:
            return web.Response(status=HTTPStatus.NOT_FOUND)

        data = await info.device_diagnostics(menuai, config_entry, device)
        return await _async_get_json_file_response(
            menuai, data, filename, config_entry.domain, d_id, sub_id
        )
