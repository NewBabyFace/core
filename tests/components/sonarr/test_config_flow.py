"""Test the Sonarr config flow."""

from unittest.mock import MagicMock, patch

from aiopyarr import ArrAuthenticationException, ArrException

from menuai.components.sonarr.const import (
    CONF_UPCOMING_DAYS,
    CONF_WANTED_MAX_ITEMS,
    DEFAULT_UPCOMING_DAYS,
    DEFAULT_WANTED_MAX_ITEMS,
    DOMAIN,
)
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_API_KEY, CONF_SOURCE, CONF_URL, CONF_VERIFY_SSL
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import MOCK_REAUTH_INPUT, MOCK_USER_INPUT

from tests.common import MockConfigEntry


async def test_show_user_form(menuai: menuai) -> None:
    """Test that the user set up form is served."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_USER},
    )

    assert result["step_id"] == "user"
    assert result["type"] is FlowResultType.FORM


async def test_cannot_connect(
    menuai: menuai, mock_sonarr_config_flow: MagicMock
) -> None:
    """Test we show user form on connection error."""
    mock_sonarr_config_flow.async_get_system_status.side_effect = ArrException

    user_input = MOCK_USER_INPUT.copy()
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_USER},
        data=user_input,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_connect"}


async def test_url_rewrite(
    menuai: menuai,
    mock_sonarr_config_flow: MagicMock,
    mock_setup_entry: None,
) -> None:
    """Test the full manual user flow from start to finish."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_USER},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    user_input = MOCK_USER_INPUT.copy()
    user_input[CONF_URL] = "https://192.168.1.189"
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=user_input,
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "192.168.1.189"

    assert result["data"]
    assert result["data"][CONF_URL] == "https://192.168.1.189:443/"


async def test_invalid_auth(
    menuai: menuai, mock_sonarr_config_flow: MagicMock
) -> None:
    """Test we show user form on invalid auth."""
    mock_sonarr_config_flow.async_get_system_status.side_effect = (
        ArrAuthenticationException
    )

    user_input = MOCK_USER_INPUT.copy()
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_USER},
        data=user_input,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "invalid_auth"}


async def test_unknown_error(
    menuai: menuai, mock_sonarr_config_flow: MagicMock
) -> None:
    """Test we show user form on unknown error."""
    mock_sonarr_config_flow.async_get_system_status.side_effect = Exception

    user_input = MOCK_USER_INPUT.copy()
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_USER},
        data=user_input,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "unknown"


async def test_full_reauth_flow_implementation(
    menuai: menuai,
    mock_sonarr_config_flow: MagicMock,
    mock_setup_entry: None,
    init_integration: MockConfigEntry,
) -> None:
    """Test the manual reauth flow from start to finish."""
    entry = init_integration

    result = await entry.start_reauth_flow(menuai)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    user_input = MOCK_REAUTH_INPUT.copy()
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input=user_input
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"

    assert entry.data[CONF_API_KEY] == "test-api-key-reauth"


async def test_full_user_flow_implementation(
    menuai: menuai,
    mock_sonarr_config_flow: MagicMock,
    mock_setup_entry: None,
) -> None:
    """Test the full manual user flow from start to finish."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_USER},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    user_input = MOCK_USER_INPUT.copy()

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=user_input,
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "192.168.1.189"

    assert result["data"]
    assert result["data"][CONF_URL] == "http://192.168.1.189:8989/"


async def test_full_user_flow_advanced_options(
    menuai: menuai,
    mock_sonarr_config_flow: MagicMock,
    mock_setup_entry: None,
) -> None:
    """Test the full manual user flow with advanced options."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={CONF_SOURCE: SOURCE_USER, "show_advanced_options": True}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    user_input = {
        **MOCK_USER_INPUT,
        CONF_VERIFY_SSL: True,
    }

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=user_input,
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "192.168.1.189"

    assert result["data"]
    assert result["data"][CONF_URL] == "http://192.168.1.189:8989/"
    assert result["data"][CONF_VERIFY_SSL]


@patch("menuai.components.sonarr.PLATFORMS", [])
async def test_options_flow(
    menuai: menuai,
    mock_setup_entry: None,
    init_integration: MockConfigEntry,
) -> None:
    """Test updating options."""
    entry = init_integration

    assert entry.options[CONF_UPCOMING_DAYS] == DEFAULT_UPCOMING_DAYS
    assert entry.options[CONF_WANTED_MAX_ITEMS] == DEFAULT_WANTED_MAX_ITEMS

    result = await menuai.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_UPCOMING_DAYS: 2, CONF_WANTED_MAX_ITEMS: 100},
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_UPCOMING_DAYS] == 2
    assert result["data"][CONF_WANTED_MAX_ITEMS] == 100
