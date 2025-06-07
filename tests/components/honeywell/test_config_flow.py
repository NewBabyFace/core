"""Tests for honeywell config flow."""

from unittest.mock import MagicMock, patch

import aiosomecomfort
import pytest

from menuai.components.honeywell.const import (
    CONF_COOL_AWAY_TEMPERATURE,
    CONF_HEAT_AWAY_TEMPERATURE,
    DOMAIN,
)
from menuai.config_entries import SOURCE_USER, ConfigEntryState
from menuai.const import CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

FAKE_CONFIG = {
    "username": "fake",
    "password": "user",
    "away_cool_temperature": 88,
    "away_heat_temperature": 61,
}


async def test_show_authenticate_form(menuai: menuai) -> None:
    """Test that the config form is shown."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_connection_error(menuai: menuai, client: MagicMock) -> None:
    """Test that an error message is shown on connection fail."""
    client.login.side_effect = aiosomecomfort.device.ConnectionError
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=FAKE_CONFIG
    )
    assert result["errors"] == {"base": "cannot_connect"}


async def test_auth_error(menuai: menuai, client: MagicMock) -> None:
    """Test that an error message is shown on login fail."""
    client.login.side_effect = aiosomecomfort.device.AuthError

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=FAKE_CONFIG
    )
    assert result["errors"] == {"base": "invalid_auth"}


async def test_create_entry(menuai: menuai) -> None:
    """Test that the config entry is created."""
    with patch(
        "menuai.components.honeywell.async_setup_entry",
        return_value=True,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=FAKE_CONFIG
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == FAKE_CONFIG


async def test_show_option_form(
    menuai: menuai, config_entry: MockConfigEntry
) -> None:
    """Test that the option form is shown."""
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    with patch(
        "menuai.components.honeywell.async_setup_entry",
        return_value=True,
    ):
        result = await menuai.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"


async def test_create_option_entry(
    menuai: menuai, config_entry: MockConfigEntry
) -> None:
    """Test that the config entry is created."""
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    with patch(
        "menuai.components.honeywell.async_setup_entry",
        return_value=True,
    ):
        options_form = await menuai.config_entries.options.async_init(
            config_entry.entry_id
        )
        result = await menuai.config_entries.options.async_configure(
            options_form["flow_id"],
            user_input={CONF_COOL_AWAY_TEMPERATURE: 1, CONF_HEAT_AWAY_TEMPERATURE: 2},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options == {
        CONF_COOL_AWAY_TEMPERATURE: 1,
        CONF_HEAT_AWAY_TEMPERATURE: 2,
    }


async def test_reauth_flow(menuai: menuai) -> None:
    """Test a successful reauth flow."""

    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_USERNAME: "test-username", CONF_PASSWORD: "test-password"},
        unique_id="test-username",
    )
    mock_entry.add_to_menuai(menuai)
    result = await mock_entry.start_reauth_flow(menuai)

    assert result["step_id"] == "reauth_confirm"
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "menuai.components.honeywell.async_setup_entry",
        return_value=True,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: "new-username", CONF_PASSWORD: "new-password"},
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "reauth_successful"
    assert mock_entry.data == {
        CONF_USERNAME: "new-username",
        CONF_PASSWORD: "new-password",
    }


async def test_reauth_flow_auth_error(menuai: menuai, client: MagicMock) -> None:
    """Test an authorization error reauth flow."""

    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_USERNAME: "test-username", CONF_PASSWORD: "test-password"},
        unique_id="test-username",
    )
    mock_entry.add_to_menuai(menuai)

    result = await mock_entry.start_reauth_flow(menuai)

    assert result["step_id"] == "reauth_confirm"
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    client.login.side_effect = aiosomecomfort.device.AuthError
    with patch(
        "menuai.components.honeywell.async_setup_entry",
        return_value=True,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: "new-username", CONF_PASSWORD: "new-password"},
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


@pytest.mark.parametrize(
    "error",
    [
        aiosomecomfort.device.ConnectionError,
        aiosomecomfort.device.ConnectionTimeout,
        TimeoutError,
    ],
)
async def test_reauth_flow_connnection_error(
    menuai: menuai, client: MagicMock, error
) -> None:
    """Test a connection error reauth flow."""

    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_USERNAME: "test-username", CONF_PASSWORD: "test-password"},
        unique_id="test-username",
    )
    mock_entry.add_to_menuai(menuai)
    result = await mock_entry.start_reauth_flow(menuai)
    assert result["step_id"] == "reauth_confirm"
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    client.login.side_effect = error

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_USERNAME: "new-username", CONF_PASSWORD: "new-password"},
    )
    await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}
