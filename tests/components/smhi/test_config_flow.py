"""Test the Smhi config flow."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from pysmhi import SmhiForecastException
import pytest

from menuai import config_entries
from menuai.components.smhi.const import DOMAIN
from menuai.components.weather import DOMAIN as WEATHER_DOMAIN
from menuai.const import CONF_LATITUDE, CONF_LOCATION, CONF_LONGITUDE
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers import device_registry as dr, entity_registry as er

from tests.common import MockConfigEntry

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


async def test_form(
    menuai: menuai,
    mock_client: MagicMock,
) -> None:
    """Test we get the form and create an entry."""

    menuai.config.latitude = 0.0
    menuai.config.longitude = 0.0

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "menuai.components.smhi.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_LOCATION: {
                    CONF_LATITUDE: 0.0,
                    CONF_LONGITUDE: 0.0,
                }
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Home"
    assert result["result"].unique_id == "0.0-0.0"
    assert result["data"] == {
        "location": {
            "latitude": 0.0,
            "longitude": 0.0,
        },
    }
    assert len(mock_setup_entry.mock_calls) == 1

    # Check title is "Weather" when not home coordinates
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_LOCATION: {
                CONF_LATITUDE: 1.0,
                CONF_LONGITUDE: 1.0,
            }
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Weather 1.0 1.0"
    assert result["data"] == {
        "location": {
            "latitude": 1.0,
            "longitude": 1.0,
        },
    }


async def test_form_invalid_coordinates(
    menuai: menuai,
    mock_client: MagicMock,
) -> None:
    """Test we handle invalid coordinates."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_client.async_get_daily_forecast.side_effect = SmhiForecastException

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_LOCATION: {
                CONF_LATITUDE: 0.0,
                CONF_LONGITUDE: 0.0,
            }
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "wrong_location"}

    # Continue flow with new coordinates
    mock_client.async_get_daily_forecast.side_effect = None
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_LOCATION: {
                CONF_LATITUDE: 2.0,
                CONF_LONGITUDE: 2.0,
            }
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Weather 2.0 2.0"
    assert result["data"] == {
        "location": {
            "latitude": 2.0,
            "longitude": 2.0,
        },
    }


async def test_form_unique_id_exist(
    menuai: menuai,
    mock_client: MagicMock,
) -> None:
    """Test we handle unique id already exist."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="1.0-1.0",
        data={
            "location": {
                "latitude": 1.0,
                "longitude": 1.0,
            },
            "name": "Weather",
        },
    )
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_LOCATION: {
                CONF_LATITUDE: 1.0,
                CONF_LONGITUDE: 1.0,
            }
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reconfigure_flow(
    menuai: menuai,
    mock_client: MagicMock,
    entity_registry: er.EntityRegistry,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test re-configuration flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        unique_id="57.2898-13.6304",
        data={"location": {"latitude": 57.2898, "longitude": 13.6304}},
        version=3,
    )
    entry.add_to_menuai(menuai)

    entity = entity_registry.async_get_or_create(
        WEATHER_DOMAIN, DOMAIN, "57.2898, 13.6304"
    )
    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "57.2898, 13.6304")},
        manufacturer="SMHI",
        model="v2",
        name=entry.title,
    )

    result = await entry.start_reconfigure_flow(menuai)
    assert result["type"] is FlowResultType.FORM

    mock_client.async_get_daily_forecast.side_effect = SmhiForecastException

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_LOCATION: {
                CONF_LATITUDE: 0.0,
                CONF_LONGITUDE: 0.0,
            }
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "wrong_location"}

    mock_client.async_get_daily_forecast.side_effect = None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_LOCATION: {
                CONF_LATITUDE: 58.2898,
                CONF_LONGITUDE: 14.6304,
            }
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    entry = menuai.config_entries.async_get_entry(entry.entry_id)
    assert entry.title == "Home"
    assert entry.unique_id == "58.2898-14.6304"
    assert entry.data == {
        "location": {
            "latitude": 58.2898,
            "longitude": 14.6304,
        },
    }
    entity = entity_registry.async_get(entity.entity_id)
    assert entity
    assert entity.unique_id == "58.2898, 14.6304"
    device = device_registry.async_get(device.id)
    assert device
    assert device.identifiers == {(DOMAIN, "58.2898, 14.6304")}
