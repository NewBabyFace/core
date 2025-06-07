"""Test the moehlenhoff_alpha2 config flow."""

from functools import partialmethod
from unittest.mock import patch

from menuai import config_entries
from menuai.components.moehlenhoff_alpha2.const import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import MOCK_BASE_HOST, mock_update_data

from tests.common import MockConfigEntry


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM
    assert not result["errors"]

    with (
        patch(
            "menuai.components.moehlenhoff_alpha2.config_flow.Alpha2Base.update_data",
            partialmethod(mock_update_data, menuai),
        ),
        patch(
            "menuai.components.moehlenhoff_alpha2.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            flow_id=result["flow_id"],
            user_input={"host": MOCK_BASE_HOST},
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Alpha2Test"
    assert result2["data"] == {"host": MOCK_BASE_HOST}
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_duplicate_error(menuai: menuai) -> None:
    """Test that errors are shown when duplicates are added."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": MOCK_BASE_HOST},
        source=config_entries.SOURCE_USER,
    )
    config_entry.add_to_menuai(menuai)

    assert config_entry.data["host"] == MOCK_BASE_HOST

    with patch(
        "moehlenhoff_alpha2.Alpha2Base.update_data",
        partialmethod(mock_update_data, menuai),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            data={"host": MOCK_BASE_HOST},
            context={"source": config_entries.SOURCE_USER},
        )
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"


async def test_form_cannot_connect_error(menuai: menuai) -> None:
    """Test connection error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch("moehlenhoff_alpha2.Alpha2Base.update_data", side_effect=TimeoutError):
        result2 = await menuai.config_entries.flow.async_configure(
            flow_id=result["flow_id"],
            user_input={"host": MOCK_BASE_HOST},
        )

        assert result2["type"] is FlowResultType.FORM
        assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_unexpected_error(menuai: menuai) -> None:
    """Test unexpected error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch("moehlenhoff_alpha2.Alpha2Base.update_data", side_effect=Exception):
        result2 = await menuai.config_entries.flow.async_configure(
            flow_id=result["flow_id"],
            user_input={"host": MOCK_BASE_HOST},
        )

        assert result2["type"] is FlowResultType.FORM
        assert result2["errors"] == {"base": "unknown"}
