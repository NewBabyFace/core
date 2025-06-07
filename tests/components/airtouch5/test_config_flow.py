"""Test the Airtouch 5 config flow."""

from unittest.mock import AsyncMock, patch

import pytest

from menuai import config_entries
from menuai.components.airtouch5.const import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


async def test_success(menuai: menuai, mock_setup_entry: AsyncMock) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    host = "1.1.1.1"

    with patch(
        "airtouch5py.airtouch5_simple_client.Airtouch5SimpleClient.test_connection",
        return_value=None,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": host,
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == host
    assert result2["data"] == {
        "host": host,
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_cannot_connect(menuai: menuai) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "airtouch5py.airtouch5_simple_client.Airtouch5SimpleClient.test_connection",
        side_effect=Exception,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.1.1.1",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}
