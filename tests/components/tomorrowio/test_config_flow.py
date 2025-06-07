"""Test the Tomorrow.io config flow."""

from unittest.mock import patch

from pytomorrowio.exceptions import (
    CantConnectException,
    InvalidAPIKeyException,
    RateLimitedException,
    UnknownException,
)

from menuai.components.tomorrowio.config_flow import (
    _get_config_schema,
    _get_unique_id,
)
from menuai.components.tomorrowio.const import (
    CONF_TIMESTEP,
    DEFAULT_NAME,
    DEFAULT_TIMESTEP,
    DOMAIN,
)
from menuai.config_entries import SOURCE_USER
from menuai.const import (
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LOCATION,
    CONF_LONGITUDE,
    CONF_NAME,
    CONF_RADIUS,
)
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.setup import async_setup_component

from .const import API_KEY, MIN_CONFIG

from tests.common import MockConfigEntry


async def test_user_flow_minimum_fields(menuai: menuai) -> None:
    """Test user config flow with minimum fields."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=_get_config_schema(menuai, SOURCE_USER, MIN_CONFIG)(MIN_CONFIG),
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == DEFAULT_NAME
    assert result["data"][CONF_NAME] == DEFAULT_NAME
    assert result["data"][CONF_API_KEY] == API_KEY
    assert result["data"][CONF_LOCATION][CONF_LATITUDE] == menuai.config.latitude
    assert result["data"][CONF_LOCATION][CONF_LONGITUDE] == menuai.config.longitude


async def test_user_flow_minimum_fields_in_zone(menuai: menuai) -> None:
    """Test user config flow with minimum fields."""
    assert await async_setup_component(
        menuai,
        "zone",
        {
            "zone": {
                CONF_NAME: "Home",
                CONF_LATITUDE: menuai.config.latitude,
                CONF_LONGITUDE: menuai.config.longitude,
                CONF_RADIUS: 100,
            }
        },
    )
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=_get_config_schema(menuai, SOURCE_USER, MIN_CONFIG)(MIN_CONFIG),
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"{DEFAULT_NAME} - Home"
    assert result["data"][CONF_NAME] == f"{DEFAULT_NAME} - Home"
    assert result["data"][CONF_API_KEY] == API_KEY
    assert result["data"][CONF_LOCATION][CONF_LATITUDE] == menuai.config.latitude
    assert result["data"][CONF_LOCATION][CONF_LONGITUDE] == menuai.config.longitude


async def test_user_flow_same_unique_ids(menuai: menuai) -> None:
    """Test user config flow with the same unique ID as an existing entry."""
    user_input = _get_config_schema(menuai, SOURCE_USER, MIN_CONFIG)(MIN_CONFIG)
    MockConfigEntry(
        domain=DOMAIN,
        data=user_input,
        options={CONF_TIMESTEP: DEFAULT_TIMESTEP},
        source=SOURCE_USER,
        unique_id=_get_unique_id(menuai, user_input),
        version=2,
    ).add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data=user_input,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_user_flow_cannot_connect(menuai: menuai) -> None:
    """Test user config flow when Tomorrow.io can't connect."""
    with patch(
        "menuai.components.tomorrowio.config_flow.TomorrowioV4.realtime",
        side_effect=CantConnectException,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data=_get_config_schema(menuai, SOURCE_USER, MIN_CONFIG)(MIN_CONFIG),
        )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_invalid_api(menuai: menuai) -> None:
    """Test user config flow when API key is invalid."""
    with patch(
        "menuai.components.tomorrowio.config_flow.TomorrowioV4.realtime",
        side_effect=InvalidAPIKeyException,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data=_get_config_schema(menuai, SOURCE_USER, MIN_CONFIG)(MIN_CONFIG),
        )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {CONF_API_KEY: "invalid_api_key"}


async def test_user_flow_rate_limited(menuai: menuai) -> None:
    """Test user config flow when API key is rate limited."""
    with patch(
        "menuai.components.tomorrowio.config_flow.TomorrowioV4.realtime",
        side_effect=RateLimitedException,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data=_get_config_schema(menuai, SOURCE_USER, MIN_CONFIG)(MIN_CONFIG),
        )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {CONF_API_KEY: "rate_limited"}


async def test_user_flow_unknown_exception(menuai: menuai) -> None:
    """Test user config flow when unknown error occurs."""
    with patch(
        "menuai.components.tomorrowio.config_flow.TomorrowioV4.realtime",
        side_effect=UnknownException,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data=_get_config_schema(menuai, SOURCE_USER, MIN_CONFIG)(MIN_CONFIG),
        )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "unknown"}


async def test_options_flow(menuai: menuai) -> None:
    """Test options config flow for tomorrowio."""
    user_config = _get_config_schema(menuai, SOURCE_USER)(MIN_CONFIG)
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=user_config,
        options={CONF_TIMESTEP: DEFAULT_TIMESTEP},
        source=SOURCE_USER,
        unique_id=_get_unique_id(menuai, user_config),
        version=1,
    )
    entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)

    assert entry.options[CONF_TIMESTEP] == DEFAULT_TIMESTEP
    assert CONF_TIMESTEP not in entry.data

    result = await menuai.config_entries.options.async_init(entry.entry_id, data=None)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_TIMESTEP: 1}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == ""
    assert result["data"][CONF_TIMESTEP] == 1
    assert entry.options[CONF_TIMESTEP] == 1
