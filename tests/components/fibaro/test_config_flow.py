"""Test the Fibaro config flow."""

from unittest.mock import Mock

from pyfibaro.fibaro_client import FibaroAuthenticationFailed, FibaroConnectFailed
import pytest

from menuai import config_entries
from menuai.components.fibaro import DOMAIN
from menuai.components.fibaro.config_flow import _normalize_url
from menuai.components.fibaro.const import CONF_IMPORT_PLUGINS
from menuai.const import CONF_PASSWORD, CONF_URL, CONF_USERNAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResult, FlowResultType

from .conftest import TEST_NAME, TEST_PASSWORD, TEST_URL, TEST_USERNAME

from tests.common import MockConfigEntry

pytestmark = pytest.mark.usefixtures("mock_setup_entry", "mock_fibaro_client")


async def _recovery_after_failure_works(
    menuai: menuai, mock_fibaro_client: Mock, result: FlowResult
) -> None:
    mock_fibaro_client.connect_with_credentials.side_effect = None
    mock_fibaro_client.connect_with_credentials.return_value = (
        mock_fibaro_client.read_info()
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_URL: TEST_URL,
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_NAME
    assert result["data"] == {
        CONF_URL: TEST_URL,
        CONF_USERNAME: TEST_USERNAME,
        CONF_PASSWORD: TEST_PASSWORD,
        CONF_IMPORT_PLUGINS: False,
    }


async def _recovery_after_reauth_failure_works(
    menuai: menuai, mock_fibaro_client: Mock, result: FlowResult
) -> None:
    mock_fibaro_client.connect_with_credentials.side_effect = None
    mock_fibaro_client.connect_with_credentials.return_value = (
        mock_fibaro_client.read_info()
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_PASSWORD: "other_fake_password"},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"


async def test_config_flow_user_initiated_success(menuai: menuai) -> None:
    """Successful flow manually initialized by the user."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_URL: TEST_URL,
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_NAME
    assert result["data"] == {
        CONF_URL: TEST_URL,
        CONF_USERNAME: TEST_USERNAME,
        CONF_PASSWORD: TEST_PASSWORD,
        CONF_IMPORT_PLUGINS: False,
    }


async def test_config_flow_user_initiated_auth_failure(
    menuai: menuai, mock_fibaro_client: Mock
) -> None:
    """Authentication failure in flow manually initialized by the user."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    mock_fibaro_client.connect_with_credentials.side_effect = (
        FibaroAuthenticationFailed()
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_URL: TEST_URL,
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "invalid_auth"}

    await _recovery_after_failure_works(menuai, mock_fibaro_client, result)


async def test_config_flow_user_initiated_connect_failure(
    menuai: menuai, mock_fibaro_client: Mock
) -> None:
    """Unknown failure in flow manually initialized by the user."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    mock_fibaro_client.connect_with_credentials.side_effect = FibaroConnectFailed()

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_URL: TEST_URL,
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_connect"}

    await _recovery_after_failure_works(menuai, mock_fibaro_client, result)


async def test_reauth_success(
    menuai: menuai, mock_config_entry: MockConfigEntry
) -> None:
    """Successful reauth flow initialized by the user."""
    result = await mock_config_entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_PASSWORD: "other_fake_password"},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"


async def test_reauth_connect_failure(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_fibaro_client: Mock,
) -> None:
    """Successful reauth flow initialized by the user."""
    result = await mock_config_entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {}

    mock_fibaro_client.connect_with_credentials.side_effect = FibaroConnectFailed()

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_PASSWORD: "other_fake_password"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {"base": "cannot_connect"}

    await _recovery_after_reauth_failure_works(menuai, mock_fibaro_client, result)


async def test_reauth_auth_failure(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_fibaro_client: Mock,
) -> None:
    """Successful reauth flow initialized by the user."""
    result = await mock_config_entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {}

    mock_fibaro_client.connect_with_credentials.side_effect = (
        FibaroAuthenticationFailed()
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_PASSWORD: "other_fake_password"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {"base": "invalid_auth"}

    await _recovery_after_reauth_failure_works(menuai, mock_fibaro_client, result)


@pytest.mark.parametrize("url_path", ["/api/", "/api", "/", ""])
async def test_normalize_url(url_path: str) -> None:
    """Test that the url is normalized for different entered values."""
    assert _normalize_url(f"http://192.168.1.1{url_path}") == "http://192.168.1.1/api/"
