"""Test the FAA Delays config flow."""

from unittest.mock import patch

from aiohttp import ClientConnectionError
import faadelays

from menuai import config_entries
from menuai.components.faa_delays.const import DOMAIN
from menuai.const import CONF_ID
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.exceptions import menuaiError

from tests.common import MockConfigEntry


async def mock_valid_airport(self, *args, **kwargs):
    """Return a valid airport."""
    self.code = "test"


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch.object(faadelays.Airport, "update", new=mock_valid_airport),
        patch(
            "menuai.components.faa_delays.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "id": "test",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "test"
    assert result2["data"] == {
        "id": "test",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_duplicate_error(menuai: menuai) -> None:
    """Test that we handle a duplicate configuration."""
    conf = {CONF_ID: "test"}

    MockConfigEntry(domain=DOMAIN, unique_id="test", data=conf).add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}, data=conf
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_form_cannot_connect(menuai: menuai) -> None:
    """Test we handle a connection error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch("faadelays.Airport.update", side_effect=ClientConnectionError):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "id": "test",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_unexpected_exception(menuai: menuai) -> None:
    """Test we handle an unexpected exception."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch("faadelays.Airport.update", side_effect=menuaiError):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "id": "test",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}
