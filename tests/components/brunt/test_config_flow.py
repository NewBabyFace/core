"""Test the Brunt config flow."""

from unittest.mock import AsyncMock, Mock, patch

from aiohttp import ClientResponseError
from aiohttp.client_exceptions import ServerDisconnectedError
import pytest

from menuai import config_entries
from menuai.components.brunt.const import DOMAIN
from menuai.const import CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

CONFIG = {CONF_USERNAME: "test-username", CONF_PASSWORD: "test-password"}

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


async def test_form(menuai: menuai, mock_setup_entry: AsyncMock) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}, data=None
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    with patch(
        "menuai.components.brunt.config_flow.BruntClientAsync.async_login",
        return_value=None,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            CONFIG,
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "test-username"
    assert result2["data"] == CONFIG
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_duplicate_login(menuai: menuai) -> None:
    """Test uniqueness of username."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=CONFIG,
        title="test-username",
        unique_id="test-username",
    )
    entry.add_to_menuai(menuai)
    with patch(
        "menuai.components.brunt.config_flow.BruntClientAsync.async_login",
        return_value=None,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=CONFIG
        )
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"


@pytest.mark.parametrize(
    ("side_effect", "error_message"),
    [
        (ServerDisconnectedError, "cannot_connect"),
        (ClientResponseError(Mock(), None, status=403), "invalid_auth"),
        (ClientResponseError(Mock(), None, status=401), "unknown"),
        (Exception, "unknown"),
    ],
)
async def test_form_error(menuai: menuai, side_effect, error_message) -> None:
    """Test we handle cannot connect."""
    with patch(
        "menuai.components.brunt.config_flow.BruntClientAsync.async_login",
        side_effect=side_effect,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=CONFIG
        )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": error_message}


@pytest.mark.parametrize(
    ("side_effect", "result_type", "password", "step_id", "reason"),
    [
        (None, FlowResultType.ABORT, "test", None, "reauth_successful"),
        (
            Exception,
            FlowResultType.FORM,
            CONFIG[CONF_PASSWORD],
            "reauth_confirm",
            None,
        ),
    ],
)
async def test_reauth(
    menuai: menuai, side_effect, result_type, password, step_id, reason
) -> None:
    """Test uniqueness of username."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=CONFIG,
        title="test-username",
        unique_id="test-username",
    )
    entry.add_to_menuai(menuai)
    result = await entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    with patch(
        "menuai.components.brunt.config_flow.BruntClientAsync.async_login",
        return_value=None,
        side_effect=side_effect,
    ):
        result3 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"password": "test"},
        )
        assert result3["type"] == result_type
        assert entry.data["password"] == password
        assert result3.get("step_id", None) == step_id
        assert result3.get("reason", None) == reason
