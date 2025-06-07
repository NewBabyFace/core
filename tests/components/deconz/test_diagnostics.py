"""Test deCONZ diagnostics."""

from pydeconz.websocket import State
from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.core import menuai

from .conftest import WebsocketStateType

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_entry_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    config_entry_setup: MockConfigEntry,
    mock_websocket_state: WebsocketStateType,
    snapshot: SnapshotAssertion,
) -> None:
    """Test config entry diagnostics."""
    await mock_websocket_state(State.RUNNING)
    await menuai.async_block_till_done()

    assert await get_diagnostics_for_config_entry(
        menuai, menuai_client, config_entry_setup
    ) == snapshot(exclude=props("created_at", "modified_at"))
