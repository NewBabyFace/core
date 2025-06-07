"""Test the Ecowitt Weather Station config flow."""

from unittest.mock import patch

from menuai import config_entries
from menuai.components.ecowitt.const import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.setup import async_setup_component


async def test_create_entry(menuai: menuai) -> None:
    """Test we can create a config entry."""
    await async_setup_component(menuai, "http", {})

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    with patch(
        "menuai.components.ecowitt.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Ecowitt"
    assert result2["data"] == {
        "webhook_id": result2["description_placeholders"]["path"].split("/")[-1],
    }
    assert len(mock_setup_entry.mock_calls) == 1
