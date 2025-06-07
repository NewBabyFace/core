"""Tests for the diagnostics data provided by the YouTube integration."""

from syrupy.assertion import SnapshotAssertion

from menuai.components.youtube.const import DOMAIN
from menuai.core import menuai

from .conftest import ComponentSetup

from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    setup_integration: ComponentSetup,
    snapshot: SnapshotAssertion,
) -> None:
    """Test diagnostics."""
    await setup_integration()
    entry = menuai.config_entries.async_entries(DOMAIN)[0]

    assert await get_diagnostics_for_config_entry(menuai, menuai_client, entry) == snapshot
