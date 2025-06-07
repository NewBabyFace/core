"""Test Radarr config flow."""

from unittest.mock import patch

from aiopyarr import exceptions
import pytest

from menuai.components.radarr.const import DEFAULT_NAME, DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_API_KEY, CONF_SOURCE, CONF_URL, CONF_VERIFY_SSL
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import (
    API_KEY,
    CONF_DATA,
    MOCK_REAUTH_INPUT,
    MOCK_USER_INPUT,
    URL,
    mock_connection,
    mock_connection_error,
    mock_connection_invalid_auth,
    patch_async_setup_entry,
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
    mock_connection_error(aioclient_mock)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_USER},
        data=MOCK_USER_INPUT,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_connect"}


async def test_invalid_auth(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test we show user form on invalid auth."""
    mock_connection_invalid_auth(aioclient_mock)
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={CONF_SOURCE: SOURCE_USER}, data=MOCK_USER_INPUT
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "invalid_auth"}


async def test_wrong_app(menuai: menuai) -> None:
    """Test we show user form on wrong app."""
    with patch(
        "menuai.components.radarr.config_flow.RadarrClient.async_try_zeroconf",
        side_effect=exceptions.ArrWrongAppException,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={CONF_SOURCE: SOURCE_USER},
            data={CONF_URL: URL, CONF_VERIFY_SSL: False},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"]["base"] == "wrong_app"


async def test_zero_conf_failure(menuai: menuai) -> None:
    """Test we show user form on api key retrieval failure."""
    with patch(
        "menuai.components.radarr.config_flow.RadarrClient.async_try_zeroconf",
        side_effect=exceptions.ArrZeroConfException,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={CONF_SOURCE: SOURCE_USER},
            data={CONF_URL: URL, CONF_VERIFY_SSL: False},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"]["base"] == "zeroconf_failed"


async def test_unknown_error(menuai: menuai) -> None:
    """Test we show user form on unknown error."""
    with patch(
        "menuai.components.radarr.config_flow.RadarrClient.async_get_system_status",
        side_effect=exceptions.ArrException,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={CONF_SOURCE: SOURCE_USER},
            data=MOCK_USER_INPUT,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "unknown"}


async def test_zero_conf(menuai: menuai) -> None:
    """Test the manual flow for zero config."""
    with patch(
        "menuai.components.radarr.config_flow.RadarrClient.async_try_zeroconf",
        return_value=("v3", API_KEY, "/test"),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={CONF_SOURCE: SOURCE_USER},
            data={CONF_URL: URL, CONF_VERIFY_SSL: False},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == DEFAULT_NAME
    assert result["data"] == CONF_DATA


async def test_url_rewrite(menuai: menuai) -> None:
    """Test auth flow url rewrite."""
    with patch(
        "menuai.components.radarr.config_flow.RadarrClient.async_try_zeroconf",
        return_value=("v3", API_KEY, "/test"),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={CONF_SOURCE: SOURCE_USER},
            data={CONF_URL: "https://192.168.1.100/test", CONF_VERIFY_SSL: False},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == DEFAULT_NAME
    assert result["data"][CONF_URL] == "https://192.168.1.100:443/test"


@pytest.mark.freeze_time("2021-12-03 00:00:00+00:00")
async def test_full_reauth_flow_implementation(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test the manual reauth flow from start to finish."""
    entry = await setup_integration(menuai, aioclient_mock)
    result = await entry.start_reauth_flow(menuai)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch_async_setup_entry() as mock_setup_entry:
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input=MOCK_REAUTH_INPUT
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"

    assert entry.data == CONF_DATA | {CONF_API_KEY: "test-api-key-reauth"}

    mock_setup_entry.assert_called_once()


async def test_full_user_flow_implementation(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test the full manual user flow from start to finish."""
    mock_connection(aioclient_mock)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_USER},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch_async_setup_entry():
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=MOCK_USER_INPUT,
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == DEFAULT_NAME
    assert result["data"] == CONF_DATA
    assert result["data"][CONF_URL] == "http://192.168.1.189:7887/test"
