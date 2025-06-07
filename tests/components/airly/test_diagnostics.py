"""Test Airly diagnostics."""

from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.core import menuai

from . import init_integration

from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.test_util.aiohttp import AiohttpClientMocker
from tests.typing import ClientSessionGenerator


async def test_entry_diagnostics(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test config entry diagnostics."""
    entry = await init_integration(menuai, aioclient_mock)

    result = await get_diagnostics_for_config_entry(menuai, menuai_client, entry)

    assert result == snapshot(exclude=props("created_at", "modified_at"))
