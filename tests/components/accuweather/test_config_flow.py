"""Define tests for the AccuWeather config flow."""

from unittest.mock import AsyncMock

from accuweather import ApiError, InvalidApiKeyError, RequestsExceededError

from menuai.components.accuweather.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_API_KEY, CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

VALID_CONFIG = {
    CONF_NAME: "abcd",
    CONF_API_KEY: "32-character-string-1234567890qw",
    CONF_LATITUDE: 55.55,
    CONF_LONGITUDE: 122.12,
}


async def test_show_form(menuai: menuai) -> None:
    """Test that the form is served with no input."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_api_key_too_short(menuai: menuai) -> None:
    """Test that errors are shown when API key is too short."""
    # The API key length check is done by the library without polling the AccuWeather
    # server so we don't need to patch the library method.
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={
            CONF_NAME: "abcd",
            CONF_API_KEY: "foo",
            CONF_LATITUDE: 55.55,
            CONF_LONGITUDE: 122.12,
        },
    )

    assert result["errors"] == {CONF_API_KEY: "invalid_api_key"}


async def test_invalid_api_key(
    menuai: menuai, mock_accuweather_client: AsyncMock
) -> None:
    """Test that errors are shown when API key is invalid."""
    mock_accuweather_client.async_get_location.side_effect = InvalidApiKeyError(
        "Invalid API key"
    )

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data=VALID_CONFIG,
    )

    assert result["errors"] == {CONF_API_KEY: "invalid_api_key"}


async def test_api_error(
    menuai: menuai, mock_accuweather_client: AsyncMock
) -> None:
    """Test API error."""
    mock_accuweather_client.async_get_location.side_effect = ApiError(
        "Invalid response from AccuWeather API"
    )

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data=VALID_CONFIG,
    )

    assert result["errors"] == {"base": "cannot_connect"}


async def test_requests_exceeded_error(
    menuai: menuai, mock_accuweather_client: AsyncMock
) -> None:
    """Test requests exceeded error."""
    mock_accuweather_client.async_get_location.side_effect = RequestsExceededError(
        "The allowed number of requests has been exceeded"
    )

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data=VALID_CONFIG,
    )

    assert result["errors"] == {CONF_API_KEY: "requests_exceeded"}


async def test_integration_already_exists(
    menuai: menuai, mock_accuweather_client: AsyncMock
) -> None:
    """Test we only allow a single config flow."""
    MockConfigEntry(
        domain=DOMAIN,
        unique_id="123456",
        data=VALID_CONFIG,
    ).add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data=VALID_CONFIG,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_create_entry(
    menuai: menuai, mock_accuweather_client: AsyncMock
) -> None:
    """Test that the user step works."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data=VALID_CONFIG,
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "abcd"
    assert result["data"][CONF_NAME] == "abcd"
    assert result["data"][CONF_LATITUDE] == 55.55
    assert result["data"][CONF_LONGITUDE] == 122.12
    assert result["data"][CONF_API_KEY] == "32-character-string-1234567890qw"
