"""Tests for the Abode config flow."""

from http import HTTPStatus
from unittest.mock import patch

from jaraco.abode.exceptions import (
    AuthenticationException as AbodeAuthenticationException,
)
from jaraco.abode.helpers.errors import MFA_CODE_REQUIRED
import pytest
from requests.exceptions import ConnectTimeout

from menuai.components.abode.const import CONF_POLLING, DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


async def test_one_config_allowed(menuai: menuai) -> None:
    """Test that only one Abode configuration is allowed."""
    MockConfigEntry(
        domain=DOMAIN,
        data={CONF_USERNAME: "user@email.com", CONF_PASSWORD: "password"},
    ).add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_user_flow(menuai: menuai) -> None:
    """Test user flow, with various errors."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    # Test that invalid credentials throws an error.
    with patch(
        "menuai.components.abode.config_flow.Abode",
        side_effect=AbodeAuthenticationException(
            (HTTPStatus.BAD_REQUEST, "auth error")
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: "user@email.com", CONF_PASSWORD: "password"},
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "invalid_auth"}

    # Test other than invalid credentials throws an error.
    with patch(
        "menuai.components.abode.config_flow.Abode",
        side_effect=AbodeAuthenticationException(
            (HTTPStatus.INTERNAL_SERVER_ERROR, "connection error")
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: "user@email.com", CONF_PASSWORD: "password"},
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_connect"}

    # Test login throws an error if connection times out.
    with patch(
        "menuai.components.abode.config_flow.Abode",
        side_effect=ConnectTimeout,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: "user@email.com", CONF_PASSWORD: "password"},
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_connect"}

    # Test success
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with patch("menuai.components.abode.config_flow.Abode"):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: "user@email.com", CONF_PASSWORD: "password"},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "user@email.com"
    assert result["data"] == {
        CONF_USERNAME: "user@email.com",
        CONF_PASSWORD: "password",
        CONF_POLLING: False,
    }


async def test_step_mfa(menuai: menuai) -> None:
    """Test that the MFA step works."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with patch(
        "menuai.components.abode.config_flow.Abode",
        side_effect=AbodeAuthenticationException(MFA_CODE_REQUIRED),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: "user@email.com", CONF_PASSWORD: "password"},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "mfa"

    with patch(
        "menuai.components.abode.config_flow.Abode",
        side_effect=AbodeAuthenticationException(
            (HTTPStatus.BAD_REQUEST, "invalid mfa")
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={"mfa_code": "123456"}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "mfa"
    assert result["errors"] == {"base": "invalid_mfa_code"}

    with patch("menuai.components.abode.config_flow.Abode"):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={"mfa_code": "123456"}
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "user@email.com"
    assert result["data"] == {
        CONF_USERNAME: "user@email.com",
        CONF_PASSWORD: "password",
        CONF_POLLING: False,
    }


async def test_step_reauth(menuai: menuai) -> None:
    """Test the reauth flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="user@email.com",
        data={CONF_USERNAME: "user@email.com", CONF_PASSWORD: "password"},
    )
    entry.add_to_menuai(menuai)

    result = await entry.start_reauth_flow(menuai)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    with (
        patch("menuai.components.abode.config_flow.Abode"),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_USERNAME: "user@email.com",
                CONF_PASSWORD: "new_password",
            },
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"

    assert len(menuai.config_entries.async_entries()) == 1
    assert entry.data[CONF_PASSWORD] == "new_password"
