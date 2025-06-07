"""Test the Anthem A/V Receivers config flow."""

from unittest.mock import AsyncMock, patch

from anthemav.device_error import DeviceError

from menuai.components.anthemav.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_form_with_valid_connection(
    menuai: menuai, mock_connection_create: AsyncMock, mock_anthemav: AsyncMock
) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    with patch(
        "menuai.components.anthemav.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.1.1.1",
                "port": 14999,
            },
        )

        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Anthem AV"
    assert result2["data"] == {
        "host": "1.1.1.1",
        "port": 14999,
        "mac": "00:00:00:00:00:01",
        "model": "MRX 520",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_device_info_error(menuai: menuai) -> None:
    """Test we handle DeviceError from library."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with patch(
        "anthemav.Connection.create",
        side_effect=DeviceError,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.1.1.1",
                "port": 14999,
            },
        )

        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_receive_deviceinfo"}


async def test_form_cannot_connect(menuai: menuai) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with patch(
        "anthemav.Connection.create",
        side_effect=OSError,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.1.1.1",
                "port": 14999,
            },
        )

        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_device_already_configured(
    menuai: menuai,
    mock_connection_create: AsyncMock,
    mock_anthemav: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test we import existing configuration."""
    config = {
        "host": "1.1.1.1",
        "port": 14999,
    }

    mock_config_entry.add_to_menuai(menuai)
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=config
    )

    assert result.get("type") is FlowResultType.ABORT
    assert result.get("reason") == "already_configured"
