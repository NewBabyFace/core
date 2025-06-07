"""Test the IMGW-PIB config flow."""

from unittest.mock import AsyncMock

from aiohttp import ClientError
from imgw_pib.exceptions import ApiError
import pytest

from menuai.components.imgw_pib.const import CONF_STATION_ID, DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType


async def test_create_entry(
    menuai: menuai, mock_setup_entry: AsyncMock, mock_imgw_pib_client: AsyncMock
) -> None:
    """Test that the user step works."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_STATION_ID: "123"},
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "River Name (Station Name)"
    assert result["data"] == {CONF_STATION_ID: "123"}
    assert result["context"]["unique_id"] == "123"
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize("exc", [ApiError("API Error"), ClientError, TimeoutError])
async def test_form_no_station_list(
    menuai: menuai, exc: Exception, mock_imgw_pib_client: AsyncMock
) -> None:
    """Test aborting the flow when we cannot get the list of hydrological stations."""
    mock_imgw_pib_client.update_hydrological_stations.side_effect = exc
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"


@pytest.mark.parametrize(
    ("exc", "base_error"),
    [
        (Exception, "unknown"),
        (ApiError("API Error"), "cannot_connect"),
        (ClientError, "cannot_connect"),
        (TimeoutError, "cannot_connect"),
    ],
)
async def test_form_with_exceptions(
    menuai: menuai,
    exc: Exception,
    base_error: str,
    mock_setup_entry: AsyncMock,
    mock_imgw_pib_client: AsyncMock,
) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    mock_imgw_pib_client.get_hydrological_data.side_effect = exc
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_STATION_ID: "123"},
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": base_error}

    mock_imgw_pib_client.get_hydrological_data.side_effect = None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_STATION_ID: "123"},
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "River Name (Station Name)"
    assert result["data"] == {CONF_STATION_ID: "123"}
    assert result["context"]["unique_id"] == "123"
    assert len(mock_setup_entry.mock_calls) == 1
