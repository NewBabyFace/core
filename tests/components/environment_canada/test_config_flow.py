"""Test the Environment Canada (EC) config flow."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch
import xml.etree.ElementTree as ET

import aiohttp
import pytest

from menuai import config_entries
from menuai.components.environment_canada.const import CONF_STATION, DOMAIN
from menuai.const import CONF_LANGUAGE, CONF_LATITUDE, CONF_LONGITUDE
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

FAKE_CONFIG = {
    CONF_STATION: "ON/s1234567",
    CONF_LANGUAGE: "English",
    CONF_LATITUDE: 42.42,
    CONF_LONGITUDE: -42.42,
}
FAKE_TITLE = "Universal title!"


def mocked_ec():
    """Mock the env_canada library."""
    ec_mock = MagicMock()
    ec_mock.station_id = FAKE_CONFIG[CONF_STATION]
    ec_mock.lat = FAKE_CONFIG[CONF_LATITUDE]
    ec_mock.lon = FAKE_CONFIG[CONF_LONGITUDE]
    ec_mock.language = FAKE_CONFIG[CONF_LANGUAGE]
    ec_mock.metadata.location = FAKE_TITLE

    ec_mock.update = AsyncMock()

    return patch(
        "menuai.components.environment_canada.config_flow.ECWeather",
        return_value=ec_mock,
    )


async def test_create_entry(menuai: menuai) -> None:
    """Test creating an entry."""
    with (
        mocked_ec(),
        patch(
            "menuai.components.environment_canada.async_setup_entry",
            return_value=True,
        ),
    ):
        flow = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await menuai.config_entries.flow.async_configure(
            flow["flow_id"], FAKE_CONFIG
        )
        await menuai.async_block_till_done()
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"] == FAKE_CONFIG
        assert result["title"] == FAKE_TITLE


async def test_create_same_entry_twice(menuai: menuai) -> None:
    """Test duplicate entries."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=FAKE_CONFIG,
        unique_id="ON/s1234567-english",
    )
    entry.add_to_menuai(menuai)

    with (
        mocked_ec(),
        patch(
            "menuai.components.environment_canada.async_setup_entry",
            return_value=True,
        ),
    ):
        flow = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await menuai.config_entries.flow.async_configure(
            flow["flow_id"], FAKE_CONFIG
        )
        await menuai.async_block_till_done()
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"


@pytest.mark.parametrize(
    "error",
    [
        (aiohttp.ClientResponseError(Mock(), (), status=404), "bad_station_id"),
        (aiohttp.ClientResponseError(Mock(), (), status=400), "error_response"),
        (aiohttp.ClientConnectionError, "cannot_connect"),
        (ET.ParseError, "bad_station_id"),
        (ValueError, "unknown"),
    ],
)
async def test_exception_handling(menuai: menuai, error) -> None:
    """Test exception handling."""
    exc, base_error = error
    with patch(
        "menuai.components.environment_canada.config_flow.ECWeather",
        side_effect=exc,
    ):
        flow = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await menuai.config_entries.flow.async_configure(
            flow["flow_id"],
            {},
        )
        await menuai.async_block_till_done()
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": base_error}


async def test_lat_lon_not_specified(menuai: menuai) -> None:
    """Test that the import step works when coordinates are not specified."""
    with (
        mocked_ec(),
        patch(
            "menuai.components.environment_canada.async_setup_entry",
            return_value=True,
        ),
    ):
        fake_config = dict(FAKE_CONFIG)
        del fake_config[CONF_LATITUDE]
        del fake_config[CONF_LONGITUDE]
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=fake_config
        )
        await menuai.async_block_till_done()
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"] == FAKE_CONFIG
        assert result["title"] == FAKE_TITLE
