"""Tests for IronOS update platform."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

from pynecil import CommunicationError, UpdateException
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.update import ATTR_INSTALLED_VERSION
from menuai.config_entries import ConfigEntryState
from menuai.const import STATE_ON, STATE_UNAVAILABLE, Platform
from menuai.core import menuai, State
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry, mock_restore_cache, snapshot_platform
from tests.typing import WebSocketGenerator


@pytest.fixture(autouse=True)
async def update_only() -> AsyncGenerator[None]:
    """Enable only the update platform."""
    with patch(
        "menuai.components.iron_os.PLATFORMS",
        [Platform.UPDATE],
    ):
        yield


@pytest.mark.usefixtures("mock_pynecil", "ble_device", "mock_ironosupdate")
async def test_update(
    menuai: menuai,
    config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    menuai_ws_client: WebSocketGenerator,
) -> None:
    """Test the IronOS update platform."""
    ws_client = await menuai_ws_client(menuai)

    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    await snapshot_platform(menuai, entity_registry, snapshot, config_entry.entry_id)

    await ws_client.send_json(
        {
            "id": 1,
            "type": "update/release_notes",
            "entity_id": "update.pinecil_firmware",
        }
    )
    result = await ws_client.receive_json()
    assert result["result"] == snapshot


@pytest.mark.usefixtures("ble_device", "mock_pynecil")
async def test_update_unavailable(
    menuai: menuai,
    config_entry: MockConfigEntry,
    mock_ironosupdate: AsyncMock,
) -> None:
    """Test update entity unavailable on error."""

    mock_ironosupdate.latest_release.side_effect = UpdateException

    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    state = menuai.states.get("update.pinecil_firmware")
    assert state is not None
    assert state.state == STATE_UNAVAILABLE


@pytest.mark.usefixtures("ble_device")
async def test_update_restore_last_state(
    menuai: menuai,
    config_entry: MockConfigEntry,
    mock_pynecil: AsyncMock,
) -> None:
    """Test update entity restore last state."""

    mock_pynecil.get_device_info.side_effect = CommunicationError
    mock_restore_cache(
        menuai,
        (
            State(
                "update.pinecil_firmware",
                STATE_ON,
                attributes={ATTR_INSTALLED_VERSION: "v2.21"},
            ),
        ),
    )
    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    state = menuai.states.get("update.pinecil_firmware")
    assert state is not None
    assert state.state == STATE_ON
    assert state.attributes[ATTR_INSTALLED_VERSION] == "v2.21"
