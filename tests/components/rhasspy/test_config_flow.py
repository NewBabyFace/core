"""Test the Rmenuaipy config flow."""

from unittest.mock import patch

from menuai import config_entries
from menuai.components.rmenuaipy.const import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    with patch(
        "menuai.components.rmenuaipy.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Rmenuaipy"
    assert result2["data"] == {}
    assert len(mock_setup_entry.mock_calls) == 1


async def test_single_entry(menuai: menuai) -> None:
    """Test we only allow single entry."""
    MockConfigEntry(domain=DOMAIN).add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"
