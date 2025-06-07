"""Test the MenuAI Cloud config flow."""

from unittest.mock import patch

from menuai.components.cloud.const import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_config_flow(menuai: menuai) -> None:
    """Test create cloud entry."""

    with (
        patch(
            "menuai.components.cloud.async_setup", return_value=True
        ) as mock_setup,
        patch(
            "menuai.components.cloud.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": "system"}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == "MenuAI Cloud"
        assert result["data"] == {}
        await menuai.async_block_till_done()

    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_multiple_entries(menuai: menuai) -> None:
    """Test creating multiple cloud entries."""
    config_entry = MockConfigEntry(domain=DOMAIN)
    config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": "system"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"
