"""Test the Apple WeatherKit config flow."""

from unittest.mock import AsyncMock, patch

from apple_weatherkit import DataSetType
from apple_weatherkit.client import (
    WeatherKitApiClientAuthenticationError,
    WeatherKitApiClientCommunicationError,
    WeatherKitApiClientError,
)
import pytest

from menuai import config_entries
from menuai.components.weatherkit.config_flow import (
    WeatherKitUnsupportedLocationError,
)
from menuai.components.weatherkit.const import (
    CONF_KEY_ID,
    CONF_KEY_PEM,
    CONF_SERVICE_ID,
    CONF_TEAM_ID,
    DOMAIN,
)
from menuai.const import CONF_LATITUDE, CONF_LOCATION, CONF_LONGITUDE
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import EXAMPLE_CONFIG_DATA

pytestmark = pytest.mark.usefixtures("mock_setup_entry")

EXAMPLE_USER_INPUT = {
    CONF_LOCATION: {
        CONF_LATITUDE: 35.4690101707532,
        CONF_LONGITUDE: 135.74817234593166,
    },
    CONF_KEY_ID: "QABCDEFG123",
    CONF_SERVICE_ID: "io.home-assistant.testing",
    CONF_TEAM_ID: "ABCD123456",
    CONF_KEY_PEM: "-----BEGIN PRIVATE KEY-----\nwhateverkey\n-----END PRIVATE KEY-----",
}


async def test_form(menuai: menuai, mock_setup_entry: AsyncMock) -> None:
    """Test we get the form and create an entry."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "menuai.components.weatherkit.WeatherKitApiClient.get_availability",
        return_value=[DataSetType.CURRENT_WEATHER],
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            EXAMPLE_USER_INPUT,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY

    location = EXAMPLE_USER_INPUT[CONF_LOCATION]
    assert result["title"] == f"{location[CONF_LATITUDE]}, {location[CONF_LONGITUDE]}"

    assert result["data"] == EXAMPLE_CONFIG_DATA
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("exception", "expected_error"),
    [
        (WeatherKitApiClientAuthenticationError, "invalid_auth"),
        (WeatherKitApiClientCommunicationError, "cannot_connect"),
        (WeatherKitUnsupportedLocationError, "unsupported_location"),
        (WeatherKitApiClientError, "unknown"),
    ],
)
async def test_error_handling(
    menuai: menuai, exception: Exception, expected_error: str
) -> None:
    """Test that we handle various exceptions and generate appropriate errors."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.weatherkit.WeatherKitApiClient.get_availability",
        side_effect=exception,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            EXAMPLE_USER_INPUT,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected_error}


async def test_form_unsupported_location(menuai: menuai) -> None:
    """Test we handle when WeatherKit does not support the location."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.weatherkit.WeatherKitApiClient.get_availability",
        return_value=[],
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            EXAMPLE_USER_INPUT,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unsupported_location"}

    # Test that we can recover from this error by changing the location
    with patch(
        "menuai.components.weatherkit.WeatherKitApiClient.get_availability",
        return_value=[DataSetType.CURRENT_WEATHER],
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            EXAMPLE_USER_INPUT,
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY


@pytest.mark.parametrize(
    ("input_header"),
    [
        "-----BEGIN PRIVATE KEY-----\n",
        "",
        "  \n\n-----BEGIN PRIVATE KEY-----\n",
        "—---BEGIN PRIVATE KEY-----\n",
    ],
    ids=["Correct header", "No header", "Leading characters", "Em dash in header"],
)
@pytest.mark.parametrize(
    ("input_footer"),
    [
        "\n-----END PRIVATE KEY-----",
        "",
        "\n-----END PRIVATE KEY-----\n\n  ",
        "\n—---END PRIVATE KEY-----",
    ],
    ids=["Correct footer", "No footer", "Trailing characters", "Em dash in footer"],
)
async def test_auto_fix_key_input(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
    input_header: str,
    input_footer: str,
) -> None:
    """Test that we fix common user errors in key input."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "menuai.components.weatherkit.WeatherKitApiClient.get_availability",
        return_value=[DataSetType.CURRENT_WEATHER],
    ):
        user_input = EXAMPLE_USER_INPUT.copy()
        user_input[CONF_KEY_PEM] = f"{input_header}whateverkey{input_footer}"
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY

    assert result["data"][CONF_KEY_PEM] == EXAMPLE_CONFIG_DATA[CONF_KEY_PEM]
    assert len(mock_setup_entry.mock_calls) == 1
