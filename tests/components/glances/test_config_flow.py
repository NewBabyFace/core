"""Tests for Glances config flow."""

from unittest.mock import MagicMock, patch

from glances_api.exceptions import (
    GlancesApiAuthorizationError,
    GlancesApiConnectionError,
    GlancesApiNoDataAvailable,
)
import pytest

from menuai import config_entries
from menuai.components.glances.const import DOMAIN
from menuai.const import CONF_NAME, CONF_USERNAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import HA_SENSOR_DATA, MOCK_USER_INPUT

from tests.common import MockConfigEntry


@pytest.fixture(autouse=True)
def glances_setup_fixture():
    """Mock glances entry setup."""
    with patch("menuai.components.glances.async_setup_entry", return_value=True):
        yield


async def test_form(menuai: menuai) -> None:
    """Test config entry configured successfully."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_USER_INPUT
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "0.0.0.0:61208"
    assert result["data"] == MOCK_USER_INPUT


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (GlancesApiAuthorizationError, "invalid_auth"),
        (GlancesApiConnectionError, "cannot_connect"),
        (GlancesApiNoDataAvailable, "cannot_connect"),
    ],
)
async def test_form_fails(
    menuai: menuai, error: Exception, message: str, mock_api: MagicMock
) -> None:
    """Test flow fails when api exception is raised."""

    mock_api.return_value.get_ha_sensor_data.side_effect = error
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_USER_INPUT
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": message}


async def test_form_already_configured(menuai: menuai) -> None:
    """Test host is already configured."""
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_INPUT)
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_USER_INPUT
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_success(menuai: menuai) -> None:
    """Test we can reauth."""
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_INPUT)
    entry.add_to_menuai(menuai)

    result = await entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["description_placeholders"] == {
        CONF_NAME: "Mock Title",
        CONF_USERNAME: "username",
    }

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "password": "new-password",
        },
    )

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "reauth_successful"


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (GlancesApiAuthorizationError, "invalid_auth"),
        (GlancesApiConnectionError, "cannot_connect"),
    ],
)
async def test_reauth_fails(
    menuai: menuai, error: Exception, message: str, mock_api: MagicMock
) -> None:
    """Test we can reauth."""
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_INPUT)
    entry.add_to_menuai(menuai)

    mock_api.return_value.get_ha_sensor_data.side_effect = [error, HA_SENSOR_DATA]
    result = await entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["description_placeholders"] == {
        CONF_NAME: "Mock Title",
        CONF_USERNAME: "username",
    }

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "password": "new-password",
        },
    )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": message}

    result3 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "password": "new-password",
        },
    )

    assert result3["type"] is FlowResultType.ABORT
    assert result3["reason"] == "reauth_successful"
