"""Test the Antifurto365 iAlarm config flow."""

from unittest.mock import patch

from menuai import config_entries
from menuai.components.ialarm.const import DOMAIN
from menuai.const import CONF_HOST, CONF_PORT
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

TEST_DATA = {CONF_HOST: "1.1.1.1", CONF_PORT: 18034}

TEST_MAC = "00:00:54:12:34:56"


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    with (
        patch(
            "menuai.components.ialarm.config_flow.IAlarm.get_status",
            return_value=1,
        ),
        patch(
            "menuai.components.ialarm.config_flow.IAlarm.get_mac",
            return_value=TEST_MAC,
        ),
        patch(
            "menuai.components.ialarm.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], TEST_DATA
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == TEST_DATA["host"]
    assert result2["data"] == TEST_DATA
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_cannot_connect(menuai: menuai) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.ialarm.config_flow.IAlarm.get_mac",
        side_effect=ConnectionError,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], TEST_DATA
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_exception(menuai: menuai) -> None:
    """Test we handle unknown exception."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.ialarm.config_flow.IAlarm.get_mac",
        side_effect=Exception,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], TEST_DATA
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}


async def test_form_already_exists(menuai: menuai) -> None:
    """Test that a flow with an existing host aborts."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=TEST_MAC,
        data=TEST_DATA,
    )

    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.ialarm.config_flow.IAlarm.get_mac",
        return_value=TEST_MAC,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], TEST_DATA
        )

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"
