"""Tests for AVM Fritz!Box config flow."""

import dataclasses
from unittest import mock
from unittest.mock import Mock, patch
from urllib.parse import urlparse

from pyfritzhome import LoginError
import pytest
from requests.exceptions import HTTPError

from menuai.components.fritzbox.const import DOMAIN
from menuai.config_entries import SOURCE_SSDP, SOURCE_USER
from menuai.const import CONF_DEVICES, CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers.service_info.ssdp import (
    ATTR_UPNP_FRIENDLY_NAME,
    ATTR_UPNP_UDN,
    SsdpServiceInfo,
)

from .const import CONF_FAKE_NAME, MOCK_CONFIG

from tests.common import MockConfigEntry

MOCK_USER_DATA = MOCK_CONFIG[DOMAIN][CONF_DEVICES][0]
MOCK_SSDP_DATA = {
    "ip4_valid": SsdpServiceInfo(
        ssdp_usn="mock_usn",
        ssdp_st="mock_st",
        ssdp_location="https://10.0.0.1:12345/test",
        upnp={
            ATTR_UPNP_FRIENDLY_NAME: CONF_FAKE_NAME,
            ATTR_UPNP_UDN: "uuid:only-a-test",
        },
    ),
    "ip6_valid": SsdpServiceInfo(
        ssdp_usn="mock_usn",
        ssdp_st="mock_st",
        ssdp_location="https://[1234::1]:12345/test",
        upnp={
            ATTR_UPNP_FRIENDLY_NAME: CONF_FAKE_NAME,
            ATTR_UPNP_UDN: "uuid:only-a-test",
        },
    ),
    "ip6_invalid": SsdpServiceInfo(
        ssdp_usn="mock_usn",
        ssdp_st="mock_st",
        ssdp_location="https://[fe80::1%1]:12345/test",
        upnp={
            ATTR_UPNP_FRIENDLY_NAME: CONF_FAKE_NAME,
            ATTR_UPNP_UDN: "uuid:only-a-test",
        },
    ),
}


@pytest.fixture(name="fritz")
def fritz_fixture() -> Mock:
    """Patch libraries."""
    with (
        patch("menuai.components.fritzbox.async_setup_entry"),
        patch("menuai.components.fritzbox.config_flow.Fritzhome") as fritz,
    ):
        yield fritz


async def test_user(menuai: menuai, fritz: Mock) -> None:
    """Test starting a flow by user."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_USER_DATA
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "10.0.0.1"
    assert result["data"][CONF_HOST] == "10.0.0.1"
    assert result["data"][CONF_PASSWORD] == "fake_pass"
    assert result["data"][CONF_USERNAME] == "fake_user"
    assert not result["result"].unique_id


async def test_user_auth_failed(menuai: menuai, fritz: Mock) -> None:
    """Test starting a flow by user with authentication failure."""
    fritz().login.side_effect = [LoginError("Boom"), mock.DEFAULT]

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=MOCK_USER_DATA
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"]["base"] == "invalid_auth"


async def test_user_not_successful(menuai: menuai, fritz: Mock) -> None:
    """Test starting a flow by user but no connection found."""
    fritz().login.side_effect = OSError("Boom")

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=MOCK_USER_DATA
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"


async def test_user_already_configured(menuai: menuai, fritz: Mock) -> None:
    """Test starting a flow by user when already configured."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=MOCK_USER_DATA
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert not result["result"].unique_id

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=MOCK_USER_DATA
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_success(menuai: menuai, fritz: Mock) -> None:
    """Test starting a reauthentication flow."""
    mock_config = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_DATA)
    mock_config.add_to_menuai(menuai)
    result = await mock_config.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_USERNAME: "other_fake_user",
            CONF_PASSWORD: "other_fake_password",
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_config.data[CONF_USERNAME] == "other_fake_user"
    assert mock_config.data[CONF_PASSWORD] == "other_fake_password"


async def test_reauth_auth_failed(menuai: menuai, fritz: Mock) -> None:
    """Test starting a reauthentication flow with authentication failure."""
    fritz().login.side_effect = LoginError("Boom")

    mock_config = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_DATA)
    mock_config.add_to_menuai(menuai)
    result = await mock_config.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_USERNAME: "other_fake_user",
            CONF_PASSWORD: "other_fake_password",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"]["base"] == "invalid_auth"


async def test_reauth_not_successful(menuai: menuai, fritz: Mock) -> None:
    """Test starting a reauthentication flow but no connection found."""
    fritz().login.side_effect = OSError("Boom")

    mock_config = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_DATA)
    mock_config.add_to_menuai(menuai)
    result = await mock_config.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_USERNAME: "other_fake_user",
            CONF_PASSWORD: "other_fake_password",
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"


async def test_reconfigure_success(menuai: menuai, fritz: Mock) -> None:
    """Test starting a reconfigure flow."""
    mock_config = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_DATA)
    mock_config.add_to_menuai(menuai)

    assert mock_config.data[CONF_HOST] == "10.0.0.1"
    assert mock_config.data[CONF_USERNAME] == "fake_user"
    assert mock_config.data[CONF_PASSWORD] == "fake_pass"

    result = await mock_config.start_reconfigure_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: "new_host",
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config.data[CONF_HOST] == "new_host"
    assert mock_config.data[CONF_USERNAME] == "fake_user"
    assert mock_config.data[CONF_PASSWORD] == "fake_pass"


async def test_reconfigure_failed(menuai: menuai, fritz: Mock) -> None:
    """Test starting a reconfigure flow with failure."""
    fritz().login.side_effect = [OSError("Boom"), None]

    mock_config = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_DATA)
    mock_config.add_to_menuai(menuai)

    assert mock_config.data[CONF_HOST] == "10.0.0.1"
    assert mock_config.data[CONF_USERNAME] == "fake_user"
    assert mock_config.data[CONF_PASSWORD] == "fake_pass"

    result = await mock_config.start_reconfigure_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: "new_host",
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    assert result["errors"]["base"] == "no_devices_found"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: "new_host",
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config.data[CONF_HOST] == "new_host"
    assert mock_config.data[CONF_USERNAME] == "fake_user"
    assert mock_config.data[CONF_PASSWORD] == "fake_pass"


@pytest.mark.parametrize(
    ("test_data", "expected_result"),
    [
        (MOCK_SSDP_DATA["ip4_valid"], FlowResultType.FORM),
        (MOCK_SSDP_DATA["ip6_valid"], FlowResultType.FORM),
        (MOCK_SSDP_DATA["ip6_invalid"], FlowResultType.ABORT),
    ],
)
async def test_ssdp(
    menuai: menuai,
    fritz: Mock,
    test_data: SsdpServiceInfo,
    expected_result: str,
) -> None:
    """Test starting a flow from discovery."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_SSDP}, data=test_data
    )
    assert result["type"] == expected_result

    if expected_result is FlowResultType.ABORT:
        return

    assert result["step_id"] == "confirm"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_PASSWORD: "fake_pass", CONF_USERNAME: "fake_user"},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == CONF_FAKE_NAME
    assert result["data"][CONF_HOST] == urlparse(test_data.ssdp_location).hostname
    assert result["data"][CONF_PASSWORD] == "fake_pass"
    assert result["data"][CONF_USERNAME] == "fake_user"
    assert result["result"].unique_id == "only-a-test"


async def test_ssdp_no_friendly_name(menuai: menuai, fritz: Mock) -> None:
    """Test starting a flow from discovery without friendly name."""
    MOCK_NO_NAME = dataclasses.replace(MOCK_SSDP_DATA["ip4_valid"])
    MOCK_NO_NAME.upnp = MOCK_NO_NAME.upnp.copy()
    del MOCK_NO_NAME.upnp[ATTR_UPNP_FRIENDLY_NAME]
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_SSDP}, data=MOCK_NO_NAME
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_PASSWORD: "fake_pass", CONF_USERNAME: "fake_user"},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "10.0.0.1"
    assert result["data"][CONF_HOST] == "10.0.0.1"
    assert result["data"][CONF_PASSWORD] == "fake_pass"
    assert result["data"][CONF_USERNAME] == "fake_user"
    assert result["result"].unique_id == "only-a-test"


async def test_ssdp_auth_failed(menuai: menuai, fritz: Mock) -> None:
    """Test starting a flow from discovery with authentication failure."""
    fritz().login.side_effect = LoginError("Boom")

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_SSDP}, data=MOCK_SSDP_DATA["ip4_valid"]
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_PASSWORD: "whatever", CONF_USERNAME: "whatever"},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"
    assert result["errors"]["base"] == "invalid_auth"


async def test_ssdp_not_successful(menuai: menuai, fritz: Mock) -> None:
    """Test starting a flow from discovery but no device found."""
    fritz().login.side_effect = OSError("Boom")

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_SSDP}, data=MOCK_SSDP_DATA["ip4_valid"]
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_PASSWORD: "whatever", CONF_USERNAME: "whatever"},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"


async def test_ssdp_not_supported(menuai: menuai, fritz: Mock) -> None:
    """Test starting a flow from discovery with unsupported device."""
    fritz().get_device_elements.side_effect = HTTPError("Boom")

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_SSDP}, data=MOCK_SSDP_DATA["ip4_valid"]
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_PASSWORD: "whatever", CONF_USERNAME: "whatever"},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_supported"


async def test_ssdp_already_in_progress_unique_id(
    menuai: menuai, fritz: Mock
) -> None:
    """Test starting a flow from discovery twice."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_SSDP}, data=MOCK_SSDP_DATA["ip4_valid"]
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_SSDP}, data=MOCK_SSDP_DATA["ip4_valid"]
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_in_progress"


async def test_ssdp_already_in_progress_host(menuai: menuai, fritz: Mock) -> None:
    """Test starting a flow from discovery twice."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_SSDP}, data=MOCK_SSDP_DATA["ip4_valid"]
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"

    MOCK_NO_UNIQUE_ID = dataclasses.replace(MOCK_SSDP_DATA["ip4_valid"])
    MOCK_NO_UNIQUE_ID.upnp = MOCK_NO_UNIQUE_ID.upnp.copy()
    del MOCK_NO_UNIQUE_ID.upnp[ATTR_UPNP_UDN]
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_SSDP}, data=MOCK_NO_UNIQUE_ID
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_in_progress"


async def test_ssdp_already_configured(menuai: menuai, fritz: Mock) -> None:
    """Test starting a flow from discovery when already configured."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=MOCK_USER_DATA
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert not result["result"].unique_id

    result2 = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_SSDP}, data=MOCK_SSDP_DATA["ip4_valid"]
    )
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"
    assert result["result"].unique_id == "only-a-test"
