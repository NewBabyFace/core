"""Tests for 1-Wire switches."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.onewire.onewirehub import _DEVICE_SCAN_INTERVAL
from menuai.components.switch import DOMAIN as SWITCH_DOMAIN
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_TOGGLE,
    STATE_OFF,
    STATE_ON,
    Platform,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_owproxy_mock_devices
from .const import MOCK_OWPROXY_DEVICES

from tests.common import MockConfigEntry, async_fire_time_changed, snapshot_platform


@pytest.fixture(autouse=True)
def override_platforms() -> Generator[None]:
    """Override PLATFORMS."""
    with patch("menuai.components.onewire._PLATFORMS", [Platform.SWITCH]):
        yield


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_switches(
    menuai: menuai,
    config_entry: MockConfigEntry,
    owproxy: MagicMock,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test for 1-Wire switch entities."""
    setup_owproxy_mock_devices(owproxy, MOCK_OWPROXY_DEVICES.keys())
    await menuai.config_entries.async_setup(config_entry.entry_id)

    await snapshot_platform(menuai, entity_registry, snapshot, config_entry.entry_id)


@pytest.mark.parametrize("device_id", ["05.111111111111"])
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_switches_delayed(
    menuai: menuai,
    config_entry: MockConfigEntry,
    owproxy: MagicMock,
    device_id: str,
    entity_registry: er.EntityRegistry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test for delayed 1-Wire switch entities."""
    setup_owproxy_mock_devices(owproxy, [])
    await menuai.config_entries.async_setup(config_entry.entry_id)

    assert not er.async_entries_for_config_entry(entity_registry, config_entry.entry_id)

    setup_owproxy_mock_devices(owproxy, [device_id])
    freezer.tick(_DEVICE_SCAN_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert (
        len(er.async_entries_for_config_entry(entity_registry, config_entry.entry_id))
        == 1
    )


@pytest.mark.parametrize("device_id", ["05.111111111111"])
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_switch_toggle(
    menuai: menuai,
    config_entry: MockConfigEntry,
    owproxy: MagicMock,
    device_id: str,
) -> None:
    """Test for 1-Wire switch TOGGLE service."""
    setup_owproxy_mock_devices(owproxy, [device_id])
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    entity_id = "switch.05_111111111111_programmed_input_output"

    # Test TOGGLE service to off
    owproxy.return_value.read.side_effect = [b"         0"]
    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TOGGLE,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    await menuai.async_block_till_done()
    assert menuai.states.get(entity_id).state == STATE_OFF

    # Test TOGGLE service to on
    owproxy.return_value.read.side_effect = [b"         1"]
    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TOGGLE,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    await menuai.async_block_till_done()
    assert menuai.states.get(entity_id).state == STATE_ON
