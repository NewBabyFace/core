"""Test the Husqvarna Automower Diagnostics."""

import datetime
from unittest.mock import AsyncMock
import zoneinfo

import pytest
from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.components.husqvarna_automower.const import DOMAIN
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from .const import TEST_MOWER_ID

from tests.common import MockConfigEntry
from tests.components.diagnostics import (
    get_diagnostics_for_config_entry,
    get_diagnostics_for_device,
)
from tests.typing import ClientSessionGenerator


@pytest.mark.freeze_time(
    datetime.datetime(2023, 6, 5, tzinfo=zoneinfo.ZoneInfo("Europe/Berlin"))
)
async def test_entry_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
    mock_automower_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test config entry diagnostics."""

    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()
    result = await get_diagnostics_for_config_entry(
        menuai, menuai_client, mock_config_entry
    )
    assert result == snapshot(exclude=props("created_at", "modified_at"))


@pytest.mark.freeze_time(
    datetime.datetime(2023, 6, 5, tzinfo=zoneinfo.ZoneInfo("Europe/Berlin"))
)
async def test_device_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
    mock_automower_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test device diagnostics platform."""

    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()
    reg_device = device_registry.async_get_device(
        identifiers={(DOMAIN, TEST_MOWER_ID)},
    )
    assert reg_device is not None
    result = await get_diagnostics_for_device(
        menuai, menuai_client, mock_config_entry, reg_device
    )
    assert result == snapshot
