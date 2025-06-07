"""Test the Rituals Perfume Genie config flow."""

from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock, patch

from aiohttp import ClientResponseError
from pyrituals import AuthenticationException

from menuai import config_entries
from menuai.components.rituals_perfume_genie.const import ACCOUNT_HASH, DOMAIN
from menuai.const import CONF_EMAIL, CONF_PASSWORD
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

TEST_EMAIL = "rituals@example.com"
VALID_PASSWORD = "passw0rd"
WRONG_PASSWORD = "wrong-passw0rd"


def _mock_account(*_):
    account = MagicMock()
    account.authenticate = AsyncMock()
    account.account_hash = "any"
    account.email = TEST_EMAIL
    return account


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    with (
        patch(
            "menuai.components.rituals_perfume_genie.config_flow.Account",
            side_effect=_mock_account,
        ),
        patch(
            "menuai.components.rituals_perfume_genie.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_EMAIL: TEST_EMAIL,
                CONF_PASSWORD: VALID_PASSWORD,
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == TEST_EMAIL
    assert isinstance(result2["data"][ACCOUNT_HASH], str)
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_auth(menuai: menuai) -> None:
    """Test we handle invalid auth."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.rituals_perfume_genie.config_flow.Account.authenticate",
        side_effect=AuthenticationException,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_EMAIL: TEST_EMAIL,
                CONF_PASSWORD: WRONG_PASSWORD,
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_auth_exception(menuai: menuai) -> None:
    """Test we handle auth exception."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.rituals_perfume_genie.config_flow.Account.authenticate",
        side_effect=Exception,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_EMAIL: TEST_EMAIL,
                CONF_PASSWORD: VALID_PASSWORD,
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}


async def test_form_cannot_connect(menuai: menuai) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.rituals_perfume_genie.config_flow.Account.authenticate",
        side_effect=ClientResponseError(
            None, None, status=HTTPStatus.INTERNAL_SERVER_ERROR
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_EMAIL: TEST_EMAIL,
                CONF_PASSWORD: VALID_PASSWORD,
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}
