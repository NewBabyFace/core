"""Test the NuHeat config flow."""

from http import HTTPStatus
from unittest.mock import MagicMock, patch

import requests

from menuai import config_entries
from menuai.components.nuheat.const import CONF_SERIAL_NUMBER, DOMAIN
from menuai.const import CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .mocks import _get_mock_thermostat_run


async def test_form_user(menuai: menuai) -> None:
    """Test we get the form with user source."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    mock_thermostat = _get_mock_thermostat_run()

    with (
        patch(
            "menuai.components.nuheat.config_flow.nuheat.NuHeat.authenticate",
            return_value=True,
        ),
        patch(
            "menuai.components.nuheat.config_flow.nuheat.NuHeat.get_thermostat",
            return_value=mock_thermostat,
        ),
        patch(
            "menuai.components.nuheat.async_setup_entry", return_value=True
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_SERIAL_NUMBER: "12345",
                CONF_USERNAME: "test-username",
                CONF_PASSWORD: "test-password",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Master bathroom"
    assert result2["data"] == {
        CONF_SERIAL_NUMBER: "12345",
        CONF_USERNAME: "test-username",
        CONF_PASSWORD: "test-password",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_auth(menuai: menuai) -> None:
    """Test we handle invalid auth."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.nuheat.config_flow.nuheat.NuHeat.authenticate",
        side_effect=Exception,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_SERIAL_NUMBER: "12345",
                CONF_USERNAME: "test-username",
                CONF_PASSWORD: "test-password",
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}

    response_mock = MagicMock()
    type(response_mock).status_code = 401
    with patch(
        "menuai.components.nuheat.config_flow.nuheat.NuHeat.authenticate",
        side_effect=requests.HTTPError(response=response_mock),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_SERIAL_NUMBER: "12345",
                CONF_USERNAME: "test-username",
                CONF_PASSWORD: "test-password",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_invalid_thermostat(menuai: menuai) -> None:
    """Test we handle invalid thermostats."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    response_mock = MagicMock()
    type(response_mock).status_code = HTTPStatus.INTERNAL_SERVER_ERROR

    with (
        patch(
            "menuai.components.nuheat.config_flow.nuheat.NuHeat.authenticate",
            return_value=True,
        ),
        patch(
            "menuai.components.nuheat.config_flow.nuheat.NuHeat.get_thermostat",
            side_effect=requests.HTTPError(response=response_mock),
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_SERIAL_NUMBER: "12345",
                CONF_USERNAME: "test-username",
                CONF_PASSWORD: "test-password",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_thermostat"}


async def test_form_cannot_connect(menuai: menuai) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.nuheat.config_flow.nuheat.NuHeat.authenticate",
        side_effect=requests.exceptions.Timeout,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_SERIAL_NUMBER: "12345",
                CONF_USERNAME: "test-username",
                CONF_PASSWORD: "test-password",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}
