"""Test the NASweb config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from webio_api.api_client import AuthError

from menuai import config_entries
from menuai.components.nasweb.const import DOMAIN
from menuai.config_entries import ConfigFlowResult
from menuai.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers.network import NoURLAvailableError

from .conftest import (
    BASE_CONFIG_FLOW,
    BASE_COORDINATOR,
    BASE_NASWEB_DATA,
    TEST_SERIAL_NUMBER,
)

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


TEST_USER_INPUT = {
    CONF_HOST: "1.1.1.1",
    CONF_USERNAME: "test-username",
    CONF_PASSWORD: "test-password",
}


async def _add_test_config_entry(menuai: menuai) -> ConfigFlowResult:
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result.get("type") == FlowResultType.FORM
    assert not result.get("errors")

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"], TEST_USER_INPUT
    )
    await menuai.async_block_till_done()
    return result2


async def test_form(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
    validate_input_all_ok: dict[str, AsyncMock | MagicMock],
) -> None:
    """Test the form."""
    result = await _add_test_config_entry(menuai)

    assert result.get("type") == FlowResultType.CREATE_ENTRY
    assert result.get("title") == "1.1.1.1"
    assert result.get("data") == TEST_USER_INPUT

    config_entry = result.get("result")
    assert config_entry is not None
    assert config_entry.unique_id == TEST_SERIAL_NUMBER
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_cannot_connect(
    menuai: menuai,
    validate_input_all_ok: dict[str, AsyncMock | MagicMock],
) -> None:
    """Test cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(BASE_CONFIG_FLOW + "WebioAPI.check_connection", return_value=False):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], TEST_USER_INPUT
        )

    assert result2.get("type") == FlowResultType.FORM
    assert result2.get("errors") == {"base": "cannot_connect"}


async def test_form_invalid_auth(
    menuai: menuai,
    validate_input_all_ok: dict[str, AsyncMock | MagicMock],
) -> None:
    """Test invalid auth."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        BASE_CONFIG_FLOW + "WebioAPI.refresh_device_info",
        side_effect=AuthError,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], TEST_USER_INPUT
        )

    assert result2.get("type") == FlowResultType.FORM
    assert result2.get("errors") == {"base": "invalid_auth"}


async def test_form_missing_internal_url(
    menuai: menuai,
    validate_input_all_ok: dict[str, AsyncMock | MagicMock],
) -> None:
    """Test missing internal url."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        BASE_NASWEB_DATA + "NASwebData.get_webhook_url", side_effect=NoURLAvailableError
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], TEST_USER_INPUT
        )
        assert result2.get("type") == FlowResultType.FORM
        assert result2.get("errors") == {"base": "missing_internal_url"}


async def test_form_missing_nasweb_data(
    menuai: menuai,
    validate_input_all_ok: dict[str, AsyncMock | MagicMock],
) -> None:
    """Test invalid auth."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        BASE_CONFIG_FLOW + "WebioAPI.get_serial_number",
        return_value=None,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], TEST_USER_INPUT
        )
        assert result2.get("type") == FlowResultType.FORM
        assert result2.get("errors") == {"base": "missing_nasweb_data"}
    with patch(BASE_CONFIG_FLOW + "WebioAPI.status_subscription", return_value=False):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], TEST_USER_INPUT
        )
        assert result2.get("type") == FlowResultType.FORM
        assert result2.get("errors") == {"base": "missing_nasweb_data"}


async def test_missing_status(
    menuai: menuai,
    validate_input_all_ok: dict[str, AsyncMock | MagicMock],
) -> None:
    """Test missing status update."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        BASE_COORDINATOR + "NotificationCoordinator.check_connection",
        return_value=False,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], TEST_USER_INPUT
        )
        assert result2.get("type") == FlowResultType.FORM
        assert result2.get("errors") == {"base": "missing_status"}


async def test_form_exception(
    menuai: menuai,
    validate_input_all_ok: dict[str, AsyncMock | MagicMock],
) -> None:
    """Test other exceptions."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.nasweb.config_flow.validate_input",
        side_effect=Exception,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], TEST_USER_INPUT
        )
        assert result2.get("type") == FlowResultType.FORM
        assert result2.get("errors") == {"base": "unknown"}


async def test_form_already_configured(
    menuai: menuai,
    validate_input_all_ok: dict[str, AsyncMock | MagicMock],
) -> None:
    """Test already configured device."""
    result = await _add_test_config_entry(menuai)
    config_entry = result.get("result")
    assert config_entry is not None
    assert config_entry.unique_id == TEST_SERIAL_NUMBER

    result2_1 = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2_2 = await menuai.config_entries.flow.async_configure(
        result2_1["flow_id"], TEST_USER_INPUT
    )
    await menuai.async_block_till_done()

    assert result2_2.get("type") == FlowResultType.ABORT
    assert result2_2.get("reason") == "already_configured"
