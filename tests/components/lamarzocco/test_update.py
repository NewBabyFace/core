"""Tests for the La Marzocco Update Entities."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

from pylamarzocco.const import FirmwareType, UpdateProgressInfo, UpdateStatus
from pylamarzocco.exceptions import RequestNotSuccessful
from pylamarzocco.models import UpdateDetails
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.update import DOMAIN as UPDATE_DOMAIN, SERVICE_INSTALL
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er

from . import async_init_integration

from tests.common import MockConfigEntry, snapshot_platform
from tests.typing import WebSocketGenerator


@pytest.fixture(autouse=True)
def mock_sleep() -> Generator[AsyncMock]:
    """Mock asyncio.sleep."""
    with patch(
        "menuai.components.lamarzocco.update.asyncio.sleep",
        return_value=AsyncMock(),
    ) as mock_sleep:
        yield mock_sleep


async def test_update(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the La Marzocco updates."""
    with patch("menuai.components.lamarzocco.PLATFORMS", [Platform.UPDATE]):
        await async_init_integration(menuai, mock_config_entry)
    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_update_process(
    menuai: menuai,
    mock_lamarzocco: MagicMock,
    mock_config_entry: MockConfigEntry,
    menuai_ws_client: WebSocketGenerator,
) -> None:
    """Test the La Marzocco update entities."""

    serial_number = mock_lamarzocco.serial_number

    mock_lamarzocco.get_firmware.side_effect = [
        UpdateDetails(
            status=UpdateStatus.TO_UPDATE,
            command_status=UpdateStatus.IN_PROGRESS,
            progress_info=UpdateProgressInfo.STARTING_PROCESS,
            progress_percentage=0,
        ),
        UpdateDetails(
            status=UpdateStatus.UPDATED,
            command_status=None,
            progress_info=None,
            progress_percentage=None,
        ),
    ]

    await async_init_integration(menuai, mock_config_entry)

    client = await menuai_ws_client(menuai)
    await menuai.async_block_till_done()

    await client.send_json(
        {
            "id": 1,
            "type": "update/release_notes",
            "entity_id": f"update.{serial_number}_gateway_firmware",
        }
    )
    result = await client.receive_json()
    assert (
        mock_lamarzocco.settings.firmwares[
            FirmwareType.GATEWAY
        ].available_update.change_log
        in result["result"]
    )

    await menuai.services.async_call(
        UPDATE_DOMAIN,
        SERVICE_INSTALL,
        {
            ATTR_ENTITY_ID: f"update.{serial_number}_gateway_firmware",
        },
        blocking=True,
    )

    mock_lamarzocco.update_firmware.assert_called_once_with()


async def test_update_error(
    menuai: menuai,
    mock_lamarzocco: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test error during update."""

    await async_init_integration(menuai, mock_config_entry)

    state = menuai.states.get(f"update.{mock_lamarzocco.serial_number}_gateway_firmware")
    assert state

    mock_lamarzocco.update_firmware.side_effect = RequestNotSuccessful("Boom")

    with pytest.raises(menuaiError) as exc_info:
        await menuai.services.async_call(
            UPDATE_DOMAIN,
            SERVICE_INSTALL,
            {
                ATTR_ENTITY_ID: f"update.{mock_lamarzocco.serial_number}_gateway_firmware",
            },
            blocking=True,
        )
    assert exc_info.value.translation_key == "update_failed"


async def test_update_times_out(
    menuai: menuai,
    mock_lamarzocco: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test error during update."""
    mock_lamarzocco.get_firmware.return_value = UpdateDetails(
        status=UpdateStatus.TO_UPDATE,
        command_status=UpdateStatus.IN_PROGRESS,
        progress_info=UpdateProgressInfo.STARTING_PROCESS,
        progress_percentage=0,
    )
    await async_init_integration(menuai, mock_config_entry)

    state = menuai.states.get(f"update.{mock_lamarzocco.serial_number}_gateway_firmware")
    assert state

    with (
        patch("menuai.components.lamarzocco.update.MAX_UPDATE_WAIT", 0),
        pytest.raises(menuaiError) as exc_info,
    ):
        await menuai.services.async_call(
            UPDATE_DOMAIN,
            SERVICE_INSTALL,
            {
                ATTR_ENTITY_ID: f"update.{mock_lamarzocco.serial_number}_gateway_firmware",
            },
            blocking=True,
        )
    assert exc_info.value.translation_key == "update_failed"
