"""Test the Tesla Fleet Diagnostics."""

from syrupy.assertion import SnapshotAssertion

from menuai.core import menuai

from . import setup_platform

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
    normal_config_entry: MockConfigEntry,
) -> None:
    """Test diagnostics."""

    await setup_platform(menuai, normal_config_entry)

    diag = await get_diagnostics_for_config_entry(
        menuai, menuai_client, normal_config_entry
    )
    assert diag == snapshot
