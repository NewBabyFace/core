"""Test the easyEnergy config flow."""

from unittest.mock import MagicMock

from menuai.components.easyenergy.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_full_user_flow(
    menuai: menuai,
    mock_setup_entry: MagicMock,
) -> None:
    """Test the full user configuration flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result.get("type") is FlowResultType.FORM
    assert result.get("step_id") == "user"
    assert "flow_id" in result

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={},
    )

    assert result2.get("type") is FlowResultType.CREATE_ENTRY
    assert result2.get("title") == "easyEnergy"
    assert result2.get("data") == {}

    assert len(mock_setup_entry.mock_calls) == 1


async def test_single_instance(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test abort when setting up a duplicate entry."""
    mock_config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result.get("type") is FlowResultType.ABORT
    assert result.get("reason") == "single_instance_allowed"
