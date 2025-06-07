"""Test the laundrify config flow."""

from laundrify_aio import exceptions

from menuai.components.laundrify.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_ACCESS_TOKEN, CONF_CODE, CONF_SOURCE
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .const import VALID_ACCESS_TOKEN, VALID_AUTH_CODE, VALID_USER_INPUT

from tests.common import MockConfigEntry


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=VALID_USER_INPUT,
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == DOMAIN
    assert result["data"] == {
        CONF_ACCESS_TOKEN: VALID_ACCESS_TOKEN,
    }
    assert result["result"].unique_id == "1234"


async def test_form_invalid_format(menuai: menuai, laundrify_api_mock) -> None:
    """Test we handle invalid format."""
    laundrify_api_mock.exchange_auth_code.side_effect = exceptions.InvalidFormat

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_USER},
        data={CONF_CODE: "invalidFormat"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_CODE: "invalid_format"}


async def test_form_invalid_auth(menuai: menuai, laundrify_api_mock) -> None:
    """Test we handle invalid auth."""
    laundrify_api_mock.exchange_auth_code.side_effect = exceptions.UnknownAuthCode
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_USER},
        data=VALID_USER_INPUT,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_CODE: "invalid_auth"}


async def test_form_cannot_connect(menuai: menuai, laundrify_api_mock) -> None:
    """Test we handle cannot connect error."""
    laundrify_api_mock.exchange_auth_code.side_effect = (
        exceptions.ApiConnectionException
    )
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_USER},
        data=VALID_USER_INPUT,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_form_unkown_exception(menuai: menuai, laundrify_api_mock) -> None:
    """Test we handle all other errors."""
    laundrify_api_mock.exchange_auth_code.side_effect = Exception
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_USER},
        data=VALID_USER_INPUT,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}


async def test_step_reauth(
    menuai: menuai, laundrify_config_entry: MockConfigEntry
) -> None:
    """Test the reauth form is shown."""
    result = await laundrify_config_entry.start_reauth_flow(menuai)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {},
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM


async def test_integration_already_exists(
    menuai: menuai, laundrify_config_entry: MockConfigEntry
) -> None:
    """Test we only allow a single config flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={CONF_SOURCE: SOURCE_USER}
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_CODE: VALID_AUTH_CODE,
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
