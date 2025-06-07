"""Test the CO2Signal diagnostics."""

from unittest.mock import MagicMock, patch

from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.components.goodwe import CONF_MODEL_FAMILY, DOMAIN
from menuai.const import CONF_HOST
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_entry_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
    mock_inverter: MagicMock,
) -> None:
    """Test config entry diagnostics."""

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "localhost", CONF_MODEL_FAMILY: "ET"},
        entry_id="3bd2acb0e4f0476d40865546d0d91921",
    )
    config_entry.add_to_menuai(menuai)
    with patch("menuai.components.goodwe.connect", return_value=mock_inverter):
        assert await async_setup_component(menuai, DOMAIN, {})

    result = await get_diagnostics_for_config_entry(menuai, menuai_client, config_entry)
    assert result == snapshot(exclude=props("created_at", "modified_at"))
