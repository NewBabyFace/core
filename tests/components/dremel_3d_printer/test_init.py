"""Test Dremel 3D Printer integration."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from requests.exceptions import ConnectTimeout

from menuai.components.dremel_3d_printer.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import STATE_UNAVAILABLE
from menuai.core import menuai
from menuai.helpers import device_registry as dr
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from tests.common import MockConfigEntry, async_fire_time_changed

MOCKED_MODEL = "menuai.components.dremel_3d_printer.Dremel3DPrinter.get_model"


@pytest.mark.parametrize("model", ["3D45", "3D20"])
async def test_setup(
    menuai: menuai, connection, config_entry: MockConfigEntry, model: str
) -> None:
    """Test load and unload."""
    with patch(MOCKED_MODEL, return_value=model) as mock:
        await menuai.config_entries.async_setup(config_entry.entry_id)
        assert await async_setup_component(menuai, DOMAIN, {})
    assert config_entry.state is ConfigEntryState.LOADED
    assert mock.called

    with patch(MOCKED_MODEL, return_value=model) as mock:
        assert await menuai.config_entries.async_unload(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.NOT_LOADED
    assert not menuai.data.get(DOMAIN)
    assert mock.called


async def test_async_setup_entry_not_ready(
    menuai: menuai, connection, config_entry: MockConfigEntry
) -> None:
    """Test that it throws ConfigEntryNotReady when exception occurs during setup."""
    with patch(
        "menuai.components.dremel_3d_printer.Dremel3DPrinter",
        side_effect=ConnectTimeout,
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
    assert await async_setup_component(menuai, DOMAIN, {})
    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert config_entry.state is ConfigEntryState.SETUP_RETRY
    assert not menuai.data.get(DOMAIN)


async def test_update_failed(
    menuai: menuai, connection, config_entry: MockConfigEntry
) -> None:
    """Test coordinator throws UpdateFailed after failed update."""
    await menuai.config_entries.async_setup(config_entry.entry_id)
    assert await async_setup_component(menuai, DOMAIN, {})
    assert config_entry.state is ConfigEntryState.LOADED

    with patch(
        "menuai.components.dremel_3d_printer.Dremel3DPrinter.refresh",
        side_effect=RuntimeError,
    ) as updater:
        next_update = dt_util.utcnow() + timedelta(seconds=10)
        async_fire_time_changed(menuai, next_update)
        await menuai.async_block_till_done()
        updater.assert_called_once()
    state = menuai.states.get("sensor.dremel_3d45_job_phase")
    assert state.state == STATE_UNAVAILABLE


async def test_device_info(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    connection,
    config_entry: MockConfigEntry,
) -> None:
    """Test device info."""
    await menuai.config_entries.async_setup(config_entry.entry_id)
    assert await async_setup_component(menuai, DOMAIN, {})
    device = device_registry.async_get_device(
        identifiers={(DOMAIN, config_entry.unique_id)}
    )

    assert device.manufacturer == "Dremel"
    assert device.model == "3D45"
    assert device.name == "DREMEL 3D45"
    assert device.sw_version == "v3.0_R02.12.10"
