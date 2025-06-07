"""Tests for the ecobee config flow."""

from unittest.mock import patch

from menuai.components.ecobee import config_flow
from menuai.components.ecobee.const import CONF_REFRESH_TOKEN, DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_API_KEY
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_abort_if_already_setup(menuai: menuai) -> None:
    """Test we abort if ecobee is already setup."""
    MockConfigEntry(domain=DOMAIN).add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_user_step_without_user_input(menuai: menuai) -> None:
    """Test expected result if user step is called."""
    flow = config_flow.EcobeeFlowHandler()
    flow.menuai = menuai

    result = await flow.async_step_user()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_pin_request_succeeds(menuai: menuai) -> None:
    """Test expected result if pin request succeeds."""
    flow = config_flow.EcobeeFlowHandler()
    flow.menuai = menuai

    with patch("menuai.components.ecobee.config_flow.Ecobee") as mock_ecobee:
        mock_ecobee = mock_ecobee.return_value
        mock_ecobee.request_pin.return_value = True
        mock_ecobee.pin = "test-pin"

        result = await flow.async_step_user(user_input={CONF_API_KEY: "api-key"})

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "authorize"
        assert result["description_placeholders"] == {"pin": "test-pin"}


async def test_pin_request_fails(menuai: menuai) -> None:
    """Test expected result if pin request fails."""
    flow = config_flow.EcobeeFlowHandler()
    flow.menuai = menuai

    with patch("menuai.components.ecobee.config_flow.Ecobee") as mock_ecobee:
        mock_ecobee = mock_ecobee.return_value
        mock_ecobee.request_pin.return_value = False

        result = await flow.async_step_user(user_input={CONF_API_KEY: "api-key"})

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"]["base"] == "pin_request_failed"


async def test_token_request_succeeds(menuai: menuai) -> None:
    """Test expected result if token request succeeds."""
    flow = config_flow.EcobeeFlowHandler()
    flow.menuai = menuai

    with patch("menuai.components.ecobee.config_flow.Ecobee") as mock_ecobee:
        mock_ecobee = mock_ecobee.return_value
        mock_ecobee.request_tokens.return_value = True
        mock_ecobee.api_key = "test-api-key"
        mock_ecobee.refresh_token = "test-token"

        flow._ecobee = mock_ecobee

        result = await flow.async_step_authorize(user_input={})

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == DOMAIN
        assert result["data"] == {
            CONF_API_KEY: "test-api-key",
            CONF_REFRESH_TOKEN: "test-token",
        }


async def test_token_request_fails(menuai: menuai) -> None:
    """Test expected result if token request fails."""
    flow = config_flow.EcobeeFlowHandler()
    flow.menuai = menuai

    with patch("menuai.components.ecobee.config_flow.Ecobee") as mock_ecobee:
        mock_ecobee = mock_ecobee.return_value
        mock_ecobee.request_tokens.return_value = False
        mock_ecobee.pin = "test-pin"

        flow._ecobee = mock_ecobee

        result = await flow.async_step_authorize(user_input={})

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "authorize"
        assert result["errors"]["base"] == "token_request_failed"
        assert result["description_placeholders"] == {"pin": "test-pin"}
