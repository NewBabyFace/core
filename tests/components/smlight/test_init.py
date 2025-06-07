"Test SMLIGHT SLZB device integration initialization."

from unittest.mock import MagicMock

from freezegun.api import FrozenDateTimeFactory
from pysmlight import Info
from pysmlight.exceptions import SmlightAuthError, SmlightConnectionError, SmlightError
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.smlight.const import (
    DOMAIN,
    SCAN_FIRMWARE_INTERVAL,
    SCAN_INTERVAL,
)
from menuai.components.update import ATTR_INSTALLED_VERSION
from menuai.config_entries import ConfigEntryState
from menuai.const import STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from menuai.core import menuai
from menuai.helpers import device_registry as dr
from menuai.helpers.issue_registry import IssueRegistry

from .conftest import setup_integration

from tests.common import MockConfigEntry, async_fire_time_changed

pytestmark = [
    pytest.mark.usefixtures(
        "mock_smlight_client",
    )
]


async def test_async_setup_entry(
    menuai: menuai, mock_config_entry: MockConfigEntry
) -> None:
    """Test async_setup_entry."""
    entry = await setup_integration(menuai, mock_config_entry)

    assert entry.state is ConfigEntryState.LOADED
    assert entry.unique_id == "aa:bb:cc:dd:ee:ff"

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_async_setup_auth_failed(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_smlight_client: MagicMock,
) -> None:
    """Test async_setup_entry when authentication fails."""
    mock_smlight_client.check_auth_needed.return_value = True
    mock_smlight_client.authenticate.side_effect = SmlightAuthError
    entry = await setup_integration(menuai, mock_config_entry)

    assert entry.state is ConfigEntryState.SETUP_ERROR

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_async_setup_missing_credentials(
    menuai: menuai,
    mock_config_entry_host: MockConfigEntry,
    mock_smlight_client: MagicMock,
) -> None:
    """Test we trigger reauth when credentials are missing."""
    mock_smlight_client.check_auth_needed.return_value = True

    await setup_integration(menuai, mock_config_entry_host)

    progress = menuai.config_entries.flow.async_progress()
    assert len(progress) == 1
    assert progress[0]["step_id"] == "reauth_confirm"
    assert progress[0]["context"]["unique_id"] == "aa:bb:cc:dd:ee:ff"


async def test_async_setup_no_internet(
    menuai: menuai,
    mock_config_entry_host: MockConfigEntry,
    mock_smlight_client: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test we still load integration when no internet is available."""
    side_effect = mock_smlight_client.get_firmware_version.side_effect
    mock_smlight_client.get_firmware_version.side_effect = SmlightConnectionError

    await setup_integration(menuai, mock_config_entry_host)

    entity = menuai.states.get("update.mock_title_core_firmware")
    assert entity is not None
    assert entity.state == STATE_UNKNOWN

    freezer.tick(SCAN_FIRMWARE_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    entity = menuai.states.get("update.mock_title_core_firmware")
    assert entity is not None
    assert entity.state == STATE_UNKNOWN

    mock_smlight_client.get_firmware_version.side_effect = side_effect

    freezer.tick(SCAN_FIRMWARE_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    entity = menuai.states.get("update.mock_title_core_firmware")
    assert entity is not None
    assert entity.state == STATE_ON
    assert entity.attributes[ATTR_INSTALLED_VERSION] == "v2.3.6"


@pytest.mark.parametrize("error", [SmlightConnectionError, SmlightAuthError])
async def test_update_failed(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_smlight_client: MagicMock,
    freezer: FrozenDateTimeFactory,
    error: SmlightError,
) -> None:
    """Test update failed due to error."""

    await setup_integration(menuai, mock_config_entry)
    entity = menuai.states.get("sensor.mock_title_core_chip_temp")
    assert entity.state is not STATE_UNAVAILABLE

    mock_smlight_client.get_info.side_effect = error

    freezer.tick(SCAN_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    entity = menuai.states.get("sensor.mock_title_core_chip_temp")
    assert entity is not None
    assert entity.state == STATE_UNAVAILABLE


async def test_device_info(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_config_entry: MockConfigEntry,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test device registry information."""
    entry = await setup_integration(menuai, mock_config_entry)

    device_entry = device_registry.async_get_device(
        connections={(dr.CONNECTION_NETWORK_MAC, entry.unique_id)}
    )
    assert device_entry is not None
    assert device_entry == snapshot


async def test_device_legacy_firmware(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_smlight_client: MagicMock,
    device_registry: dr.DeviceRegistry,
    issue_registry: IssueRegistry,
) -> None:
    """Test device setup for old firmware version that dont support required API."""
    LEGACY_VERSION = "v0.9.9"
    mock_smlight_client.get_sensors.side_effect = SmlightError
    mock_smlight_client.get_info.side_effect = None
    mock_smlight_client.get_info.return_value = Info(
        legacy_api=2, sw_version=LEGACY_VERSION, MAC="AA:BB:CC:DD:EE:FF"
    )
    entry = await setup_integration(menuai, mock_config_entry)

    assert entry.unique_id == "aa:bb:cc:dd:ee:ff"

    device_entry = device_registry.async_get_device(
        connections={(dr.CONNECTION_NETWORK_MAC, entry.unique_id)}
    )
    assert LEGACY_VERSION in device_entry.sw_version

    issue = issue_registry.async_get_issue(
        domain=DOMAIN, issue_id="unsupported_firmware"
    )
    assert issue is not None
    assert issue.domain == DOMAIN
    assert issue.issue_id == "unsupported_firmware"
