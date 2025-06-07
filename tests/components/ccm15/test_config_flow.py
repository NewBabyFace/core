"""Test the Midea ccm15 AC Controller config flow."""

from unittest.mock import AsyncMock, patch

from menuai import config_entries
from menuai.components.ccm15.const import DOMAIN
from menuai.const import CONF_HOST, CONF_PORT
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_form(menuai: menuai, mock_setup_entry: AsyncMock) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "ccm15.CCM15Device.CCM15Device.async_test_connection",
        return_value=True,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "1.1.1.1"
    assert result2["data"] == {
        CONF_HOST: "1.1.1.1",
        CONF_PORT: 80,
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_host(
    menuai: menuai, mock_setup_entry: AsyncMock
) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "ccm15.CCM15Device.CCM15Device.async_test_connection",
        return_value=False,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}
    assert len(mock_setup_entry.mock_calls) == 0

    with patch(
        "ccm15.CCM15Device.CCM15Device.async_test_connection", return_value=True
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.0.0.1",
            },
        )

    assert result2["type"] is FlowResultType.CREATE_ENTRY


async def test_form_cannot_connect(menuai: menuai) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "ccm15.CCM15Device.CCM15Device.async_test_connection", return_value=False
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}

    with patch(
        "ccm15.CCM15Device.CCM15Device.async_test_connection", return_value=True
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.0.0.1",
            },
        )

    assert result2["type"] is FlowResultType.CREATE_ENTRY


async def test_form_unexpected_error(menuai: menuai) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "ccm15.CCM15Device.CCM15Device.async_test_connection",
        side_effect=Exception(),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}

    with patch(
        "ccm15.CCM15Device.CCM15Device.async_test_connection", return_value=True
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.0.0.1",
            },
        )

    assert result2["type"] is FlowResultType.CREATE_ENTRY


async def test_duplicate_host(menuai: menuai, mock_setup_entry: AsyncMock) -> None:
    """Test we handle cannot connect error."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="1.1.1.1",
        data={
            CONF_HOST: "1.1.1.1",
            CONF_PORT: 80,
        },
    )
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: "1.1.1.1",
            CONF_PORT: 80,
        },
    )

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"
