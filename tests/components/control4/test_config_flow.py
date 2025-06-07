"""Test the Control4 config flow."""

from unittest.mock import AsyncMock, patch

from pyControl4.account import C4Account
from pyControl4.director import C4Director
from pyControl4.error_handling import Unauthorized

from menuai import config_entries
from menuai.components.control4.const import DEFAULT_SCAN_INTERVAL, DOMAIN
from menuai.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


def _get_mock_c4_account():
    c4_account_mock = AsyncMock(C4Account)

    c4_account_mock.getAccountControllers.return_value = {
        "controllerCommonName": "control4_model_00AA00AA00AA",
        "href": "https://apis.control4.com/account/v3/rest/accounts/000000",
        "name": "Name",
    }

    c4_account_mock.getDirectorBearerToken.return_value = {"token": "token"}

    return c4_account_mock


def _get_mock_c4_director():
    c4_director_mock = AsyncMock(C4Director)
    c4_director_mock.getAllItemInfo.return_value = {}

    return c4_director_mock


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    c4_account = _get_mock_c4_account()
    c4_director = _get_mock_c4_director()
    with (
        patch(
            "menuai.components.control4.config_flow.C4Account",
            return_value=c4_account,
        ),
        patch(
            "menuai.components.control4.config_flow.C4Director",
            return_value=c4_director,
        ),
        patch(
            "menuai.components.control4.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
                CONF_USERNAME: "test-username",
                CONF_PASSWORD: "test-password",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "control4_model_00AA00AA00AA"
    assert result2["data"] == {
        CONF_HOST: "1.1.1.1",
        CONF_USERNAME: "test-username",
        CONF_PASSWORD: "test-password",
        "controller_unique_id": "control4_model_00AA00AA00AA",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_auth(menuai: menuai) -> None:
    """Test we handle invalid auth."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.control4.config_flow.C4Account",
        side_effect=Unauthorized("message"),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
                CONF_USERNAME: "test-username",
                CONF_PASSWORD: "test-password",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_unexpected_exception(menuai: menuai) -> None:
    """Test we handle an unexpected exception."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.control4.config_flow.C4Account",
        side_effect=ValueError("message"),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
                CONF_USERNAME: "test-username",
                CONF_PASSWORD: "test-password",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}


async def test_form_cannot_connect(menuai: menuai) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with (
        patch(
            "menuai.components.control4.config_flow.Control4Validator.authenticate",
            return_value=True,
        ),
        patch(
            "menuai.components.control4.config_flow.C4Director",
            side_effect=Unauthorized("message"),
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
                CONF_USERNAME: "test-username",
                CONF_PASSWORD: "test-password",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_option_flow(menuai: menuai) -> None:
    """Test config flow options."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, options=None)
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_SCAN_INTERVAL: 4},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_SCAN_INTERVAL: 4,
    }


async def test_option_flow_defaults(menuai: menuai) -> None:
    """Test config flow options."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, options=None)
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"], user_input={}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
    }
