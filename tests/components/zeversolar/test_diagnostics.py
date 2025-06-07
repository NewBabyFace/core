"""Tests for the diagnostics data provided by the Zeversolar integration."""

from syrupy.assertion import SnapshotAssertion

from menuai.components.zeversolar import DOMAIN
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from . import MOCK_SERIAL_NUMBER, init_integration

from tests.components.diagnostics import (
    get_diagnostics_for_config_entry,
    get_diagnostics_for_device,
)
from tests.typing import ClientSessionGenerator


async def test_entry_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test config entry diagnostics."""

    entry = await init_integration(menuai)

    assert await get_diagnostics_for_config_entry(menuai, menuai_client, entry) == snapshot


async def test_device_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    device_registry: dr.DeviceRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test device diagnostics."""

    entry = await init_integration(menuai)

    device = device_registry.async_get_device(
        identifiers={(DOMAIN, MOCK_SERIAL_NUMBER)}
    )

    assert (
        await get_diagnostics_for_device(menuai, menuai_client, entry, device) == snapshot
    )
