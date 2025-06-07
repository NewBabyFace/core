"""Test Netgear LTE integration."""

from datetime import timedelta
from unittest.mock import patch

from eternalegypt.eternalegypt import Error
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.netgear_lte.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import STATE_UNAVAILABLE
from menuai.core import menuai
from menuai.helpers import device_registry as dr
from menuai.util import dt as dt_util

from .conftest import CONF_DATA

from tests.common import async_fire_time_changed


@pytest.mark.usefixtures("setup_integration")
async def test_setup_unload(menuai: menuai) -> None:
    """Test setup and unload."""
    entry = menuai.config_entries.async_entries(DOMAIN)[0]
    assert entry.state is ConfigEntryState.LOADED
    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.data == CONF_DATA

    await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert not menuai.data.get(DOMAIN)


@pytest.mark.usefixtures("setup_cannot_connect")
async def test_async_setup_entry_not_ready(menuai: menuai) -> None:
    """Test that it throws ConfigEntryNotReady when exception occurs during setup."""
    entry = menuai.config_entries.async_entries(DOMAIN)[0]
    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.usefixtures("setup_integration")
async def test_device(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test device info."""
    entry = menuai.config_entries.async_entries(DOMAIN)[0]
    await menuai.async_block_till_done()
    device = device_registry.async_get_device(identifiers={(DOMAIN, entry.unique_id)})
    assert device == snapshot


@pytest.mark.usefixtures("entity_registry_enabled_by_default", "setup_integration")
async def test_update_failed(menuai: menuai) -> None:
    """Test coordinator throws UpdateFailed after failed update."""
    with patch(
        "menuai.components.netgear_lte.eternalegypt.Modem.information",
        side_effect=Error,
    ) as updater:
        next_update = dt_util.utcnow() + timedelta(seconds=10)
        async_fire_time_changed(menuai, next_update)
        await menuai.async_block_till_done()
        updater.assert_called_once()
    state = menuai.states.get("sensor.netgear_lm1200_radio_quality")
    assert state.state == STATE_UNAVAILABLE
