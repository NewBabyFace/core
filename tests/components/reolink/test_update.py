"""Test the Reolink update platform."""

import asyncio
from datetime import timedelta
from unittest.mock import MagicMock, patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from reolink_aio.exceptions import ApiError, ReolinkError
from reolink_aio.software_version import NewSoftwareVersion

from menuai.components.reolink.update import POLL_AFTER_INSTALL, POLL_PROGRESS
from menuai.components.update import DOMAIN as UPDATE_DOMAIN, SERVICE_INSTALL
from menuai.config_entries import ConfigEntryState
from menuai.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON, Platform
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.util.dt import utcnow

from .conftest import TEST_CAM_NAME, TEST_NVR_NAME

from tests.common import MockConfigEntry, async_fire_time_changed
from tests.typing import WebSocketGenerator

TEST_DOWNLOAD_URL = "https://reolink.com/test"
TEST_RELEASE_NOTES = "bugfix 1, bugfix 2"


@pytest.mark.parametrize("entity_name", [TEST_NVR_NAME, TEST_CAM_NAME])
async def test_no_update(
    menuai: menuai,
    config_entry: MockConfigEntry,
    reolink_connect: MagicMock,
    entity_name: str,
) -> None:
    """Test update state when no update available."""
    reolink_connect.camera_name.return_value = TEST_CAM_NAME

    with patch("menuai.components.reolink.PLATFORMS", [Platform.UPDATE]):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED

    entity_id = f"{Platform.UPDATE}.{entity_name}_firmware"
    assert menuai.states.get(entity_id).state == STATE_OFF


@pytest.mark.parametrize("entity_name", [TEST_NVR_NAME, TEST_CAM_NAME])
async def test_update_str(
    menuai: menuai,
    config_entry: MockConfigEntry,
    reolink_connect: MagicMock,
    entity_name: str,
) -> None:
    """Test update state when update available with string from API."""
    reolink_connect.camera_name.return_value = TEST_CAM_NAME
    reolink_connect.firmware_update_available.return_value = "New firmware available"

    with patch("menuai.components.reolink.PLATFORMS", [Platform.UPDATE]):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED

    entity_id = f"{Platform.UPDATE}.{entity_name}_firmware"
    assert menuai.states.get(entity_id).state == STATE_ON


@pytest.mark.parametrize("entity_name", [TEST_NVR_NAME, TEST_CAM_NAME])
async def test_update_firm(
    menuai: menuai,
    config_entry: MockConfigEntry,
    reolink_connect: MagicMock,
    menuai_ws_client: WebSocketGenerator,
    freezer: FrozenDateTimeFactory,
    entity_name: str,
) -> None:
    """Test update state when update available with firmware info from reolink.com."""
    reolink_connect.camera_name.return_value = TEST_CAM_NAME
    reolink_connect.sw_upload_progress.return_value = 100
    reolink_connect.camera_sw_version.return_value = "v1.1.0.0.0.0000"
    new_firmware = NewSoftwareVersion(
        version_string="v3.3.0.226_23031644",
        download_url=TEST_DOWNLOAD_URL,
        release_notes=TEST_RELEASE_NOTES,
    )
    reolink_connect.firmware_update_available.return_value = new_firmware

    with patch("menuai.components.reolink.PLATFORMS", [Platform.UPDATE]):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED

    entity_id = f"{Platform.UPDATE}.{entity_name}_firmware"
    assert menuai.states.get(entity_id).state == STATE_ON
    assert not menuai.states.get(entity_id).attributes["in_progress"]
    assert menuai.states.get(entity_id).attributes["update_percentage"] is None

    # release notes
    client = await menuai_ws_client(menuai)
    await menuai.async_block_till_done()

    await client.send_json(
        {
            "id": 1,
            "type": "update/release_notes",
            "entity_id": entity_id,
        }
    )
    result = await client.receive_json()
    assert TEST_DOWNLOAD_URL in result["result"]
    assert TEST_RELEASE_NOTES in result["result"]

    # test install
    await menuai.services.async_call(
        UPDATE_DOMAIN,
        SERVICE_INSTALL,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    reolink_connect.update_firmware.assert_called()

    reolink_connect.sw_upload_progress.return_value = 50
    freezer.tick(POLL_PROGRESS)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert menuai.states.get(entity_id).attributes["in_progress"]
    assert menuai.states.get(entity_id).attributes["update_percentage"] == 50

    reolink_connect.sw_upload_progress.return_value = 100
    freezer.tick(POLL_AFTER_INSTALL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert not menuai.states.get(entity_id).attributes["in_progress"]
    assert menuai.states.get(entity_id).attributes["update_percentage"] is None

    reolink_connect.update_firmware.side_effect = ReolinkError("Test error")
    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            UPDATE_DOMAIN,
            SERVICE_INSTALL,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )

    reolink_connect.update_firmware.side_effect = ApiError(
        "Test error", translation_key="firmware_rate_limit"
    )
    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            UPDATE_DOMAIN,
            SERVICE_INSTALL,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )

    # test _async_update_future
    reolink_connect.camera_sw_version.return_value = "v3.3.0.226_23031644"
    reolink_connect.firmware_update_available.return_value = False
    freezer.tick(POLL_AFTER_INSTALL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert menuai.states.get(entity_id).state == STATE_OFF

    reolink_connect.update_firmware.side_effect = None


@pytest.mark.parametrize("entity_name", [TEST_NVR_NAME, TEST_CAM_NAME])
async def test_update_firm_keeps_available(
    menuai: menuai,
    config_entry: MockConfigEntry,
    reolink_connect: MagicMock,
    menuai_ws_client: WebSocketGenerator,
    entity_name: str,
) -> None:
    """Test update entity keeps being available during update."""
    reolink_connect.camera_name.return_value = TEST_CAM_NAME
    reolink_connect.camera_sw_version.return_value = "v1.1.0.0.0.0000"
    new_firmware = NewSoftwareVersion(
        version_string="v3.3.0.226_23031644",
        download_url=TEST_DOWNLOAD_URL,
        release_notes=TEST_RELEASE_NOTES,
    )
    reolink_connect.firmware_update_available.return_value = new_firmware

    with patch("menuai.components.reolink.PLATFORMS", [Platform.UPDATE]):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED

    entity_id = f"{Platform.UPDATE}.{entity_name}_firmware"
    assert menuai.states.get(entity_id).state == STATE_ON

    async def mock_update_firmware(*args, **kwargs) -> None:
        await asyncio.sleep(0.000005)

    reolink_connect.update_firmware = mock_update_firmware

    # test install
    with patch("menuai.components.reolink.update.POLL_PROGRESS", 0.000001):
        await menuai.services.async_call(
            UPDATE_DOMAIN,
            SERVICE_INSTALL,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )

    reolink_connect.session_active = False
    async_fire_time_changed(menuai, utcnow() + timedelta(seconds=1))
    await menuai.async_block_till_done()

    # still available
    assert menuai.states.get(entity_id).state == STATE_ON

    reolink_connect.session_active = True
