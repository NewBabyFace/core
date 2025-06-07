"""Test august diagnostics."""

from syrupy.assertion import SnapshotAssertion

from menuai.core import menuai

from .mocks import (
    _create_august_api_with_devices,
    _mock_doorbell_from_fixture,
    _mock_lock_from_fixture,
)

from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test generating diagnostics for a config entry."""
    lock_one = await _mock_lock_from_fixture(
        menuai, "get_lock.online_with_doorsense.json"
    )
    doorbell_one = await _mock_doorbell_from_fixture(menuai, "get_doorbell.json")

    entry, _ = await _create_august_api_with_devices(menuai, [lock_one, doorbell_one])
    diag = await get_diagnostics_for_config_entry(menuai, menuai_client, entry)

    assert diag == snapshot
