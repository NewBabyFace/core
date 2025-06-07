"""Test the Reolink sensor platform."""

from unittest.mock import MagicMock, patch

import pytest

from menuai.config_entries import ConfigEntryState
from menuai.const import STATE_UNAVAILABLE, Platform
from menuai.core import menuai

from .conftest import TEST_NVR_NAME

from tests.common import MockConfigEntry


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensors(
    menuai: menuai,
    config_entry: MockConfigEntry,
    reolink_connect: MagicMock,
) -> None:
    """Test sensor entities."""
    reolink_connect.ptz_pan_position.return_value = 1200
    reolink_connect.wifi_connection = True
    reolink_connect.wifi_signal = 3
    reolink_connect.hdd_list = [0]
    reolink_connect.hdd_storage.return_value = 95

    with patch("menuai.components.reolink.PLATFORMS", [Platform.SENSOR]):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED

    entity_id = f"{Platform.SENSOR}.{TEST_NVR_NAME}_ptz_pan_position"
    assert menuai.states.get(entity_id).state == "1200"

    entity_id = f"{Platform.SENSOR}.{TEST_NVR_NAME}_wi_fi_signal"
    assert menuai.states.get(entity_id).state == "3"

    entity_id = f"{Platform.SENSOR}.{TEST_NVR_NAME}_sd_0_storage"
    assert menuai.states.get(entity_id).state == "95"


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_hdd_sensors(
    menuai: menuai,
    config_entry: MockConfigEntry,
    reolink_connect: MagicMock,
) -> None:
    """Test hdd sensor entity."""
    reolink_connect.hdd_list = [0]
    reolink_connect.hdd_type.return_value = "HDD"
    reolink_connect.hdd_storage.return_value = 85
    reolink_connect.hdd_available.return_value = False

    with patch("menuai.components.reolink.PLATFORMS", [Platform.SENSOR]):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED

    entity_id = f"{Platform.SENSOR}.{TEST_NVR_NAME}_hdd_0_storage"
    assert menuai.states.get(entity_id).state == STATE_UNAVAILABLE
