"""Test Simplepush config flow."""

from unittest.mock import patch

import pytest
from simplepush import UnknownError

from menuai import config_entries
from menuai.components.simplepush.const import CONF_DEVICE_KEY, CONF_SALT, DOMAIN
from menuai.const import CONF_NAME, CONF_PASSWORD
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

MOCK_CONFIG = {
    CONF_DEVICE_KEY: "abc",
    CONF_NAME: "simplepush",
}


@pytest.fixture(autouse=True)
def simplepush_setup_fixture():
    """Patch simplepush setup entry."""
    with patch(
        "menuai.components.simplepush.async_setup_entry", return_value=True
    ):
        yield


@pytest.fixture(autouse=True)
def mock_api_request():
    """Patch simplepush api request."""
    with patch("menuai.components.simplepush.config_flow.send"):
        yield


async def test_flow_successful(menuai: menuai) -> None:
    """Test user initialized flow with minimum config."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_CONFIG,
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "simplepush"
    assert result["data"] == MOCK_CONFIG


async def test_flow_with_password(menuai: menuai) -> None:
    """Test user initialized flow with password and salt."""
    mock_config_pass = {**MOCK_CONFIG, CONF_PASSWORD: "password", CONF_SALT: "salt"}
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=mock_config_pass,
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "simplepush"
    assert result["data"] == mock_config_pass


async def test_flow_user_device_key_already_configured(menuai: menuai) -> None:
    """Test user initialized flow with duplicate device key."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG,
        unique_id="abc",
    )

    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_CONFIG,
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_flow_user_name_already_configured(menuai: menuai) -> None:
    """Test user initialized flow with duplicate name."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG,
        unique_id="abc",
    )

    entry.add_to_menuai(menuai)

    new_entry = MOCK_CONFIG.copy()
    new_entry[CONF_DEVICE_KEY] = "abc1"

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_CONFIG,
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_error_on_connection_failure(menuai: menuai) -> None:
    """Test when connection to api fails."""
    with patch(
        "menuai.components.simplepush.config_flow.send",
        side_effect=UnknownError,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=MOCK_CONFIG,
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}
