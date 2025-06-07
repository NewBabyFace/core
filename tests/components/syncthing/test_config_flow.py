"""Tests for syncthing config flow."""

from unittest.mock import patch

from aiosyncthing.exceptions import UnauthorizedError

from menuai import config_entries
from menuai.components.syncthing.const import DOMAIN
from menuai.const import CONF_NAME, CONF_TOKEN, CONF_URL, CONF_VERIFY_SSL
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

NAME = "Syncthing"
URL = "http://127.0.0.1:8384"
TOKEN = "token"
VERIFY_SSL = True

MOCK_ENTRY = {
    CONF_NAME: NAME,
    CONF_URL: URL,
    CONF_TOKEN: TOKEN,
    CONF_VERIFY_SSL: VERIFY_SSL,
}


async def test_show_setup_form(menuai: menuai) -> None:
    """Test that the setup form is served."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}
    assert result["step_id"] == "user"


async def test_flow_successful(menuai: menuai) -> None:
    """Test with required fields only."""
    with (
        patch("aiosyncthing.system.System.status", return_value={"myID": "server-id"}),
        patch(
            "menuai.components.syncthing.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
            data={
                CONF_NAME: NAME,
                CONF_URL: URL,
                CONF_TOKEN: TOKEN,
                CONF_VERIFY_SSL: VERIFY_SSL,
            },
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == "http://127.0.0.1:8384"
        assert result["data"][CONF_NAME] == NAME
        assert result["data"][CONF_URL] == URL
        assert result["data"][CONF_TOKEN] == TOKEN
        assert result["data"][CONF_VERIFY_SSL] == VERIFY_SSL
        assert len(mock_setup_entry.mock_calls) == 1


async def test_flow_already_configured(menuai: menuai) -> None:
    """Test name is already configured."""

    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_ENTRY, unique_id="server-id")
    entry.add_to_menuai(menuai)

    with patch("aiosyncthing.system.System.status", return_value={"myID": "server-id"}):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
            data=MOCK_ENTRY,
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_flow_invalid_auth(menuai: menuai) -> None:
    """Test invalid auth."""

    with patch("aiosyncthing.system.System.status", side_effect=UnauthorizedError):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
            data=MOCK_ENTRY,
        )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"]["token"] == "invalid_auth"


async def test_flow_cannot_connect(menuai: menuai) -> None:
    """Test cannot connect."""

    with patch("aiosyncthing.system.System.status", side_effect=Exception):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
            data=MOCK_ENTRY,
        )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"]["base"] == "cannot_connect"
