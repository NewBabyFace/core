"""Tests for the Diagnostics integration."""

from http import HTTPStatus
from typing import cast

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.device_registry import DeviceEntry
from menuai.setup import async_setup_component
from menuai.util.json import JsonObjectType

from tests.typing import ClientSessionGenerator


async def _get_diagnostics_for_config_entry(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    config_entry: ConfigEntry,
) -> JsonObjectType:
    """Return the diagnostics config entry for the specified domain."""
    assert await async_setup_component(menuai, "diagnostics", {})
    await menuai.async_block_till_done()

    client = await menuai_client()
    response = await client.get(
        f"/api/diagnostics/config_entry/{config_entry.entry_id}"
    )
    assert response.status == HTTPStatus.OK
    return cast(JsonObjectType, await response.json())


async def get_diagnostics_for_config_entry(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    config_entry: ConfigEntry,
) -> JsonObjectType:
    """Return the diagnostics config entry for the specified domain."""
    data = await _get_diagnostics_for_config_entry(menuai, menuai_client, config_entry)
    return cast(JsonObjectType, data["data"])


async def _get_diagnostics_for_device(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    config_entry: ConfigEntry,
    device: DeviceEntry,
) -> JsonObjectType:
    """Return the diagnostics for the specified device."""
    assert await async_setup_component(menuai, "diagnostics", {})

    client = await menuai_client()
    response = await client.get(
        f"/api/diagnostics/config_entry/{config_entry.entry_id}/device/{device.id}"
    )
    assert response.status == HTTPStatus.OK
    return cast(JsonObjectType, await response.json())


async def get_diagnostics_for_device(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    config_entry: ConfigEntry,
    device: DeviceEntry,
) -> JsonObjectType:
    """Return the diagnostics for the specified device."""
    data = await _get_diagnostics_for_device(menuai, menuai_client, config_entry, device)
    return cast(JsonObjectType, data["data"])
