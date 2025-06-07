"""Test pushbullet config flow."""

from unittest.mock import patch

from pushbullet import InvalidKeyError, PushbulletError
import pytest

from menuai import config_entries
from menuai.components.pushbullet.const import DOMAIN
from menuai.const import CONF_API_KEY
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import MOCK_CONFIG

from tests.common import MockConfigEntry


@pytest.fixture(autouse=True)
def pushbullet_setup_fixture():
    """Patch pushbullet setup entry."""
    with patch(
        "menuai.components.pushbullet.async_setup_entry", return_value=True
    ):
        yield


async def test_flow_user(menuai: menuai, requests_mock_fixture) -> None:
    """Test user initialized flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_CONFIG,
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "pushbullet"
    assert result["data"] == MOCK_CONFIG


async def test_flow_user_already_configured(
    menuai: menuai, requests_mock_fixture
) -> None:
    """Test user initialized flow with duplicate server."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG,
        unique_id="ujpah72o0",
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


async def test_flow_name_already_configured(menuai: menuai) -> None:
    """Test user initialized flow with duplicate server."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG,
        unique_id="MYAPIKEY",
    )

    entry.add_to_menuai(menuai)

    new_config = MOCK_CONFIG.copy()
    new_config[CONF_API_KEY] = "NEWKEY"

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=new_config,
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_flow_invalid_key(menuai: menuai) -> None:
    """Test user initialized flow with invalid api key."""

    with patch(
        "menuai.components.pushbullet.config_flow.PushBullet",
        side_effect=InvalidKeyError,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data=MOCK_CONFIG,
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {CONF_API_KEY: "invalid_api_key"}


async def test_flow_conn_error(menuai: menuai) -> None:
    """Test user initialized flow with conn error."""

    with patch(
        "menuai.components.pushbullet.config_flow.PushBullet",
        side_effect=PushbulletError,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data=MOCK_CONFIG,
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_connect"}
