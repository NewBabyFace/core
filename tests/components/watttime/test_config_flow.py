"""Test the WattTime config flow."""

from unittest.mock import AsyncMock, patch

from aiowatttime.errors import CoordinatesNotFoundError, InvalidCredentialsError
import pytest

from menuai import config_entries
from menuai.components.watttime.config_flow import (
    CONF_LOCATION_TYPE,
    LOCATION_TYPE_HOME,
)
from menuai.components.watttime.const import (
    CONF_BALANCING_AUTHORITY,
    CONF_BALANCING_AUTHORITY_ABBREV,
    DOMAIN,
)
from menuai.const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_PASSWORD,
    CONF_SHOW_ON_MAP,
    CONF_USERNAME,
)
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


@pytest.mark.parametrize(
    ("exc", "error"),
    [(InvalidCredentialsError, "invalid_auth"), (Exception, "unknown")],
)
async def test_auth_errors(
    menuai: menuai, config_auth, config_location_type, exc, error
) -> None:
    """Test that issues with auth show the correct error."""
    with patch(
        "menuai.components.watttime.config_flow.Client.async_login",
        side_effect=exc,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=config_auth
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": error}


@pytest.mark.parametrize(
    ("get_grid_region", "errors"),
    [
        (
            AsyncMock(side_effect=CoordinatesNotFoundError),
            {"latitude": "unknown_coordinates"},
        ),
        (
            AsyncMock(side_effect=Exception),
            {"base": "unknown"},
        ),
    ],
)
async def test_coordinate_errors(
    menuai: menuai,
    config_auth,
    config_coordinates,
    config_location_type,
    errors,
    setup_watttime,
) -> None:
    """Test that issues with coordinates show the correct error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}, data=config_auth
    )
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input=config_location_type
    )
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input=config_coordinates
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == errors


@pytest.mark.parametrize(
    "config_location_type", [{CONF_LOCATION_TYPE: LOCATION_TYPE_HOME}]
)
async def test_duplicate_error(
    menuai: menuai, config_auth, config_entry, config_location_type, setup_watttime
) -> None:
    """Test that errors are shown when duplicate entries are added."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}, data=config_auth
    )
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input=config_location_type
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow(menuai: menuai, config_entry) -> None:
    """Test config flow options."""
    with patch(
        "menuai.components.watttime.async_setup_entry", return_value=True
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        result = await menuai.config_entries.options.async_init(config_entry.entry_id)
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "init"

        result = await menuai.config_entries.options.async_configure(
            result["flow_id"], user_input={CONF_SHOW_ON_MAP: False}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert config_entry.options == {CONF_SHOW_ON_MAP: False}


async def test_show_form_coordinates(
    menuai: menuai, config_auth, config_location_type, setup_watttime
) -> None:
    """Test showing the form to input custom latitude/longitude."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input=config_auth
    )
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input=config_location_type
    )
    result = await menuai.config_entries.flow.async_configure(result["flow_id"])
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "coordinates"
    assert result["errors"] is None


async def test_show_form_user(menuai: menuai) -> None:
    """Test showing the form to select the authentication type."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] is None


async def test_step_reauth(
    menuai: menuai,
    config_entry: MockConfigEntry,
    setup_watttime,
) -> None:
    """Test a full reauth flow."""
    result = await config_entry.start_reauth_flow(menuai)
    with patch(
        "menuai.components.watttime.async_setup_entry",
        return_value=True,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_PASSWORD: "password"},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert len(menuai.config_entries.async_entries()) == 1


async def test_step_user_coordinates(
    menuai: menuai,
    config_auth,
    config_location_type,
    config_coordinates,
    setup_watttime,
) -> None:
    """Test a full login flow (inputting custom coordinates)."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}, data=config_auth
    )
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input=config_location_type
    )
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input=config_coordinates
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "32.87336, -117.22743"
    assert result["data"] == {
        CONF_USERNAME: "user",
        CONF_PASSWORD: "password",
        CONF_LATITUDE: 32.87336,
        CONF_LONGITUDE: -117.22743,
        CONF_BALANCING_AUTHORITY: "PJM New Jersey",
        CONF_BALANCING_AUTHORITY_ABBREV: "PJM_NJ",
    }


@pytest.mark.parametrize(
    "config_location_type", [{CONF_LOCATION_TYPE: LOCATION_TYPE_HOME}]
)
async def test_step_user_home(
    menuai: menuai, config_auth, config_location_type, setup_watttime
) -> None:
    """Test a full login flow (selecting the home location)."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}, data=config_auth
    )
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input=config_location_type
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "32.87336, -117.22743"
    assert result["data"] == {
        CONF_USERNAME: "user",
        CONF_PASSWORD: "password",
        CONF_LATITUDE: 32.87336,
        CONF_LONGITUDE: -117.22743,
        CONF_BALANCING_AUTHORITY: "PJM New Jersey",
        CONF_BALANCING_AUTHORITY_ABBREV: "PJM_NJ",
    }
