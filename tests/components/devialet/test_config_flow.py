"""Test the Devialet config flow."""

from unittest.mock import patch

from aiohttp import ClientError as HTTPClientError
from devialet.const import UrlSuffix

from menuai.components.devialet.const import DOMAIN
from menuai.config_entries import SOURCE_USER, SOURCE_ZEROCONF
from menuai.const import CONF_HOST, CONF_NAME, CONF_SOURCE
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import (
    HOST,
    MOCK_USER_INPUT,
    MOCK_ZEROCONF_DATA,
    NAME,
    mock_playing,
    setup_integration,
)

from tests.test_util.aiohttp import AiohttpClientMocker


async def test_show_user_form(menuai: menuai) -> None:
    """Test that the user set up form is served."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_USER},
    )

    assert result["step_id"] == "user"
    assert result["type"] is FlowResultType.FORM


async def test_cannot_connect(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test we show user form on connection error."""
    aioclient_mock.get(
        f"http://{HOST}{UrlSuffix.GET_GENERAL_INFO}", exc=HTTPClientError
    )

    user_input = MOCK_USER_INPUT.copy()
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_USER},
        data=user_input,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_device_exists_abort(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test we abort user flow if DirecTV receiver already configured."""
    await setup_integration(menuai, aioclient_mock, skip_entry_setup=True)

    user_input = MOCK_USER_INPUT.copy()
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_USER},
        data=user_input,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_full_user_flow_implementation(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test the full manual user flow from start to finish."""
    mock_playing(aioclient_mock)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_USER},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    user_input = MOCK_USER_INPUT.copy()
    with patch(
        "menuai.components.devialet.async_setup_entry", return_value=True
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=user_input,
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == NAME

    assert result["data"]
    assert result["data"][CONF_HOST] == HOST


async def test_zeroconf_devialet(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test we pass Devialet devices to the discovery manager."""
    mock_playing(aioclient_mock)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=MOCK_ZEROCONF_DATA
    )

    assert result["type"] is FlowResultType.FORM

    with patch(
        "menuai.components.devialet.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Livingroom"
    assert result2["data"] == {
        CONF_HOST: HOST,
        CONF_NAME: NAME,
    }

    assert len(mock_setup_entry.mock_calls) == 1


async def test_async_step_confirm(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test starting a flow from discovery."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=MOCK_ZEROCONF_DATA
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"

    aioclient_mock.get(
        f"http://{HOST}{UrlSuffix.GET_GENERAL_INFO}", exc=HTTPClientError
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_USER_INPUT.copy()
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"
    assert result["errors"] == {"base": "cannot_connect"}
