"""Tests for eafm config flow."""

from unittest.mock import patch

import pytest
from voluptuous.error import Invalid

from menuai import config_entries
from menuai.components.eafm import const
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType


async def test_flow_no_discovered_stations(
    menuai: menuai, mock_get_stations
) -> None:
    """Test config flow discovers no station."""
    mock_get_stations.return_value = []
    result = await menuai.config_entries.flow.async_init(
        const.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_stations"


async def test_flow_invalid_station(menuai: menuai, mock_get_stations) -> None:
    """Test config flow errors on invalid station."""
    mock_get_stations.return_value = [
        {"label": "My station", "stationReference": "L12345"}
    ]

    result = await menuai.config_entries.flow.async_init(
        const.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    with pytest.raises(Invalid):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={"station": "My other station"}
        )


async def test_flow_works(
    menuai: menuai, mock_get_stations, mock_get_station
) -> None:
    """Test config flow discovers no station."""
    mock_get_stations.return_value = [
        {"label": "My station", "stationReference": "L12345"}
    ]
    mock_get_station.return_value = [
        {"label": "My station", "stationReference": "L12345"}
    ]

    result = await menuai.config_entries.flow.async_init(
        const.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    with patch("menuai.components.eafm.async_setup_entry", return_value=True):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={"station": "My station"}
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "My station"
    assert result["data"] == {
        "station": "L12345",
    }
