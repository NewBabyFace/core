"""Common methods used across tests for Bond."""

from __future__ import annotations

from contextlib import nullcontext
from datetime import timedelta
from typing import Any
from unittest.mock import MagicMock, patch

from aiohttp.client_exceptions import ClientResponseError
from bond_async import DeviceType

from menuai import core
from menuai.components.bond.const import DOMAIN
from menuai.const import CONF_ACCESS_TOKEN, CONF_HOST, STATE_UNAVAILABLE
from menuai.setup import async_setup_component
from menuai.util import utcnow

from tests.common import MockConfigEntry, async_fire_time_changed


def ceiling_fan_with_breeze(name: str):
    """Create a ceiling fan with given name with breeze support."""
    return {
        "name": name,
        "type": DeviceType.CEILING_FAN,
        "actions": ["SetSpeed", "SetDirection", "BreezeOn"],
    }


def patch_setup_entry(domain: str, *, enabled: bool = True):
    """Patch async_setup_entry for specified domain."""
    if not enabled:
        return nullcontext()

    return patch(f"menuai.components.bond.{domain}.async_setup_entry")


async def setup_bond_entity(
    menuai: core.menuai,
    config_entry: MockConfigEntry,
    *,
    patch_version=False,
    patch_device_ids=False,
    patch_platforms=False,
    patch_bridge=False,
    patch_token=False,
):
    """Set up Bond entity."""
    config_entry.add_to_menuai(menuai)

    with (
        patch_start_bpup(),
        patch_bond_bridge(enabled=patch_bridge),
        patch_bond_token(enabled=patch_token),
        patch_bond_version(enabled=patch_version),
        patch_bond_device_ids(enabled=patch_device_ids),
        patch_setup_entry("cover", enabled=patch_platforms),
        patch_setup_entry("fan", enabled=patch_platforms),
        patch_setup_entry("light", enabled=patch_platforms),
        patch_setup_entry("switch", enabled=patch_platforms),
    ):
        return await menuai.config_entries.async_setup(config_entry.entry_id)


async def setup_platform(
    menuai: core.menuai,
    platform: str,
    discovered_device: dict[str, Any],
    *,
    bond_device_id: str = "bond-device-id",
    bond_version: dict[str, Any] | None = None,
    props: dict[str, Any] | None = None,
    state: dict[str, Any] | None = None,
    bridge: dict[str, Any] | None = None,
    token: dict[str, Any] | None = None,
):
    """Set up the specified Bond platform."""
    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "some host", CONF_ACCESS_TOKEN: "test-token"},
    )
    mock_entry.add_to_menuai(menuai)

    with (
        patch("menuai.components.bond.PLATFORMS", [platform]),
        patch_bond_version(return_value=bond_version),
        patch_bond_bridge(return_value=bridge),
        patch_bond_token(return_value=token),
        patch_bond_device_ids(return_value=[bond_device_id]),
        patch_start_bpup(),
        patch_bond_device(return_value=discovered_device),
        patch_bond_device_properties(return_value=props),
        patch_bond_device_state(return_value=state),
    ):
        assert await async_setup_component(menuai, DOMAIN, {})
        await menuai.async_block_till_done()

    return mock_entry


def patch_bond_version(
    enabled: bool = True, return_value: dict | None = None, side_effect=None
):
    """Patch Bond API version endpoint."""
    if not enabled:
        return nullcontext()

    if return_value is None:
        return_value = {
            "bondid": "ZXXX12345",
            "target": "test-model",
            "fw_ver": "test-version",
            "mcu_ver": "test-hw-version",
        }

    return patch(
        "menuai.components.bond.Bond.version",
        return_value=return_value,
        side_effect=side_effect,
    )


def patch_bond_bridge(
    enabled: bool = True, return_value: dict | None = None, side_effect=None
):
    """Patch Bond API bridge endpoint."""
    if not enabled:
        return nullcontext()

    if return_value is None:
        return_value = {
            "name": "bond-name",
            "location": "bond-location",
            "bluelight": 127,
        }

    return patch(
        "menuai.components.bond.Bond.bridge",
        return_value=return_value,
        side_effect=side_effect,
    )


def patch_bond_token(
    enabled: bool = True, return_value: dict | None = None, side_effect=None
):
    """Patch Bond API token endpoint."""
    if not enabled:
        return nullcontext()

    if return_value is None:
        return_value = {"locked": 1}

    return patch(
        "menuai.components.bond.Bond.token",
        return_value=return_value,
        side_effect=side_effect,
    )


def patch_bond_device_ids(enabled: bool = True, return_value=None, side_effect=None):
    """Patch Bond API devices endpoint."""
    if not enabled:
        return nullcontext()

    if return_value is None:
        return_value = []

    return patch(
        "menuai.components.bond.Bond.devices",
        return_value=return_value,
        side_effect=side_effect,
    )


def patch_bond_device(return_value=None):
    """Patch Bond API device endpoint."""
    return patch(
        "menuai.components.bond.Bond.device",
        return_value=return_value,
    )


def patch_start_bpup():
    """Patch start_bpup."""
    return patch(
        "menuai.components.bond.start_bpup",
        return_value=MagicMock(),
    )


def patch_bond_action():
    """Patch Bond API action endpoint."""
    return patch("menuai.components.bond.Bond.action")


def patch_bond_action_returns_clientresponseerror():
    """Patch Bond API action endpoint to throw ClientResponseError."""
    return patch(
        "menuai.components.bond.Bond.action",
        side_effect=ClientResponseError(
            request_info=None, history=None, status=405, message="Method Not Allowed"
        ),
    )


def patch_bond_device_properties(return_value=None):
    """Patch Bond API device properties endpoint."""
    if return_value is None:
        return_value = {}

    return patch(
        "menuai.components.bond.Bond.device_properties",
        return_value=return_value,
    )


def patch_bond_device_state(return_value=None, side_effect=None):
    """Patch Bond API device state endpoint."""
    if return_value is None:
        return_value = {}

    return patch(
        "menuai.components.bond.Bond.device_state",
        return_value=return_value,
        side_effect=side_effect,
    )


async def help_test_entity_available(
    menuai: core.menuai, domain: str, device: dict[str, Any], entity_id: str
):
    """Run common test to verify available property."""
    await setup_platform(menuai, domain, device)

    assert menuai.states.get(entity_id).state != STATE_UNAVAILABLE

    with patch_bond_device_state(side_effect=TimeoutError()):
        async_fire_time_changed(menuai, utcnow() + timedelta(seconds=30))
        await menuai.async_block_till_done()
    assert menuai.states.get(entity_id).state == STATE_UNAVAILABLE

    with patch_bond_device_state(return_value={}):
        async_fire_time_changed(menuai, utcnow() + timedelta(seconds=30))
        await menuai.async_block_till_done()
    assert menuai.states.get(entity_id).state != STATE_UNAVAILABLE


def ceiling_fan(name: str):
    """Create a ceiling fan with given name."""
    return {
        "name": name,
        "type": DeviceType.CEILING_FAN,
        "actions": ["SetSpeed", "SetDirection"],
    }
