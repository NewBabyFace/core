"""Test RainMachine diagnostics."""

from regenmaschine.errors import RainMachineError
from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.core import menuai

from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_entry_diagnostics(
    menuai: menuai,
    config_entry,
    menuai_client: ClientSessionGenerator,
    setup_rainmachine,
    snapshot: SnapshotAssertion,
) -> None:
    """Test config entry diagnostics."""
    assert await get_diagnostics_for_config_entry(
        menuai, menuai_client, config_entry
    ) == snapshot(exclude=props("created_at", "modified_at"))


async def test_entry_diagnostics_failed_controller_diagnostics(
    menuai: menuai,
    config_entry,
    controller,
    menuai_client: ClientSessionGenerator,
    setup_rainmachine,
    snapshot: SnapshotAssertion,
) -> None:
    """Test config entry diagnostics when the controller diagnostics API call fails."""
    controller.diagnostics.current.side_effect = RainMachineError
    assert await get_diagnostics_for_config_entry(
        menuai, menuai_client, config_entry
    ) == snapshot(exclude=props("created_at", "modified_at"))
