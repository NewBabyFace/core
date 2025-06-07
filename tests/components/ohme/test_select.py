"""Tests for selects."""

from unittest.mock import AsyncMock, MagicMock, patch

from ohme import ChargerMode
from syrupy.assertion import SnapshotAssertion

from menuai.const import STATE_UNAVAILABLE, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, snapshot_platform


async def test_selects(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
) -> None:
    """Test the Ohme selects."""
    with patch("menuai.components.ohme.PLATFORMS", [Platform.SELECT]):
        await setup_integration(menuai, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_select_option(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
) -> None:
    """Test selecting an option in the Ohme select entity."""
    mock_client.mode = ChargerMode.SMART_CHARGE
    mock_client.async_set_mode = AsyncMock()

    await setup_integration(menuai, mock_config_entry)

    state = menuai.states.get("select.ohme_home_pro_charge_mode")
    assert state is not None
    assert state.state == "smart_charge"

    await menuai.services.async_call(
        "select",
        "select_option",
        {
            "entity_id": "select.ohme_home_pro_charge_mode",
            "option": "max_charge",
        },
        blocking=True,
    )

    mock_client.async_set_mode.assert_called_once_with("max_charge")
    assert state.state == "smart_charge"


async def test_select_unavailable(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
) -> None:
    """Test that the select entity shows as unavailable when no mode is set."""
    mock_client.mode = None

    await setup_integration(menuai, mock_config_entry)

    state = menuai.states.get("select.ohme_home_pro_charge_mode")
    assert state is not None
    assert state.state == STATE_UNAVAILABLE
