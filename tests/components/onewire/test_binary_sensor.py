"""Tests for 1-Wire binary sensors."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.onewire.onewirehub import _DEVICE_SCAN_INTERVAL
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_owproxy_mock_devices
from .const import MOCK_OWPROXY_DEVICES

from tests.common import MockConfigEntry, async_fire_time_changed, snapshot_platform


@pytest.fixture(autouse=True)
def override_platforms() -> Generator[None]:
    """Override PLATFORMS."""
    with patch("menuai.components.onewire._PLATFORMS", [Platform.BINARY_SENSOR]):
        yield


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_binary_sensors(
    menuai: menuai,
    config_entry: MockConfigEntry,
    owproxy: MagicMock,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test for 1-Wire binary sensor entities."""
    setup_owproxy_mock_devices(owproxy, MOCK_OWPROXY_DEVICES.keys())
    await menuai.config_entries.async_setup(config_entry.entry_id)

    await snapshot_platform(menuai, entity_registry, snapshot, config_entry.entry_id)


@pytest.mark.parametrize("device_id", ["29.111111111111"])
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_binary_sensors_delayed(
    menuai: menuai,
    config_entry: MockConfigEntry,
    owproxy: MagicMock,
    device_id: str,
    entity_registry: er.EntityRegistry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test for delayed 1-Wire binary sensor entities."""
    setup_owproxy_mock_devices(owproxy, [])
    await menuai.config_entries.async_setup(config_entry.entry_id)

    assert not er.async_entries_for_config_entry(entity_registry, config_entry.entry_id)

    setup_owproxy_mock_devices(owproxy, [device_id])
    freezer.tick(_DEVICE_SCAN_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert (
        len(er.async_entries_for_config_entry(entity_registry, config_entry.entry_id))
        == 8
    )
