"""Test the GPSD config flow."""

from unittest.mock import AsyncMock, patch

from gps3.agps3threaded import GPSD_PORT as DEFAULT_PORT

from menuai import config_entries
from menuai.components.gpsd.const import DOMAIN
from menuai.const import CONF_HOST, CONF_PORT
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

HOST = "gpsd.local"


async def test_form(menuai: menuai, mock_setup_entry: AsyncMock) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    with patch("socket.socket") as mock_socket:
        mock_connect = mock_socket.return_value.connect
        mock_connect.return_value = None

        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: HOST,
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == f"GPS {HOST}"
    assert result2["data"] == {
        CONF_HOST: HOST,
        CONF_PORT: DEFAULT_PORT,
    }
    mock_setup_entry.assert_called_once()


async def test_connection_error(menuai: menuai) -> None:
    """Test connection to host error."""
    with patch("socket.socket", side_effect=OSError):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={CONF_HOST: "nonexistent.local", CONF_PORT: 1234},
        )

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "cannot_connect"
