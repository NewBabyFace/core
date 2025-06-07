"""Test for vesync config flow."""

from unittest.mock import patch

from menuai.components.vesync import DOMAIN, config_flow
from menuai.const import CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_abort_already_setup(menuai: menuai) -> None:
    """Test if we abort because component is already setup."""
    flow = config_flow.VeSyncFlowHandler()
    flow.menuai = menuai
    MockConfigEntry(domain=DOMAIN, title="user", data={"user": "pass"}).add_to_menuai(
        menuai
    )
    result = await flow.async_step_user()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_invalid_login_error(menuai: menuai) -> None:
    """Test if we return error for invalid username and password."""
    test_dict = {CONF_USERNAME: "user", CONF_PASSWORD: "pass"}
    flow = config_flow.VeSyncFlowHandler()
    flow.menuai = menuai
    with patch("pyvesync.vesync.VeSync.login", return_value=False):
        result = await flow.async_step_user(user_input=test_dict)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_config_flow_user_input(menuai: menuai) -> None:
    """Test config flow with user input."""
    flow = config_flow.VeSyncFlowHandler()
    flow.menuai = menuai
    result = await flow.async_step_user()
    assert result["type"] is FlowResultType.FORM
    with patch("pyvesync.vesync.VeSync.login", return_value=True):
        result = await flow.async_step_user(
            {CONF_USERNAME: "user", CONF_PASSWORD: "pass"}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_USERNAME] == "user"
        assert result["data"][CONF_PASSWORD] == "pass"


async def test_reauth_flow(menuai: menuai) -> None:
    """Test a successful reauth flow."""
    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="test-username",
    )
    mock_entry.add_to_menuai(menuai)

    result = await mock_entry.start_reauth_flow(menuai)

    assert result["step_id"] == "reauth_confirm"
    assert result["type"] is FlowResultType.FORM
    with patch("pyvesync.vesync.VeSync.login", return_value=True):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: "new-username", CONF_PASSWORD: "new-password"},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_entry.data == {
        CONF_USERNAME: "new-username",
        CONF_PASSWORD: "new-password",
    }


async def test_reauth_flow_invalid_auth(menuai: menuai) -> None:
    """Test an authorization error reauth flow."""

    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="test-username",
    )
    mock_entry.add_to_menuai(menuai)

    result = await mock_entry.start_reauth_flow(menuai)
    assert result["step_id"] == "reauth_confirm"
    assert result["type"] is FlowResultType.FORM

    with patch("pyvesync.vesync.VeSync.login", return_value=False):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: "new-username", CONF_PASSWORD: "new-password"},
        )

    assert result["type"] is FlowResultType.FORM
    with patch("pyvesync.vesync.VeSync.login", return_value=True):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: "new-username", CONF_PASSWORD: "new-password"},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
