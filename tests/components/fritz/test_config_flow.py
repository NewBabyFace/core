"""Tests for Fritz!Tools config flow."""

from copy import deepcopy
import dataclasses
from unittest.mock import patch

from fritzconnection.core.exceptions import (
    FritzAuthorizationError,
    FritzConnectionException,
    FritzSecurityError,
)
import pytest

from menuai.components.device_tracker import (
    CONF_CONSIDER_HOME,
    DEFAULT_CONSIDER_HOME,
)
from menuai.components.fritz.const import (
    CONF_FEATURE_DEVICE_TRACKING,
    CONF_OLD_DISCOVERY,
    DOMAIN,
    ERROR_AUTH_INVALID,
    ERROR_CANNOT_CONNECT,
    ERROR_UNKNOWN,
    ERROR_UPNP_NOT_CONFIGURED,
    FRITZ_AUTH_EXCEPTIONS,
)
from menuai.config_entries import SOURCE_SSDP, SOURCE_USER
from menuai.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
)
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers.service_info.ssdp import (
    ATTR_UPNP_FRIENDLY_NAME,
    ATTR_UPNP_UDN,
    SsdpServiceInfo,
)

from .conftest import FritzConnectionMock
from .const import (
    MOCK_FB_SERVICES,
    MOCK_FIRMWARE_INFO,
    MOCK_IPS,
    MOCK_REQUEST,
    MOCK_SSDP_DATA,
    MOCK_USER_DATA,
    MOCK_USER_INPUT_ADVANCED,
    MOCK_USER_INPUT_SIMPLE,
)

from tests.common import MockConfigEntry


@pytest.mark.parametrize(
    ("show_advanced_options", "user_input", "expected_config"),
    [
        (
            True,
            MOCK_USER_INPUT_ADVANCED,
            {
                CONF_HOST: "fake_host",
                CONF_PASSWORD: "fake_pass",
                CONF_USERNAME: "fake_user",
                CONF_PORT: 1234,
                CONF_SSL: False,
            },
        ),
        (
            False,
            MOCK_USER_INPUT_SIMPLE,
            {
                CONF_HOST: "fake_host",
                CONF_PASSWORD: "fake_pass",
                CONF_USERNAME: "fake_user",
                CONF_PORT: 49000,
                CONF_SSL: False,
            },
        ),
        (
            False,
            {**MOCK_USER_INPUT_SIMPLE, CONF_SSL: True},
            {
                CONF_HOST: "fake_host",
                CONF_PASSWORD: "fake_pass",
                CONF_USERNAME: "fake_user",
                CONF_PORT: 49443,
                CONF_SSL: True,
            },
        ),
    ],
)
async def test_user(
    menuai: menuai,
    fc_class_mock,
    show_advanced_options: bool,
    user_input: dict,
    expected_config: dict,
) -> None:
    """Test starting a flow by user."""
    with (
        patch(
            "menuai.components.fritz.config_flow.FritzConnection",
            side_effect=fc_class_mock,
        ),
        patch(
            "menuai.components.fritz.coordinator.FritzBoxTools._update_device_info",
            return_value=MOCK_FIRMWARE_INFO,
        ),
        patch("menuai.components.fritz.async_setup_entry") as mock_setup_entry,
        patch(
            "requests.get",
        ) as mock_request_get,
        patch(
            "requests.post",
        ) as mock_request_post,
        patch(
            "menuai.components.fritz.config_flow.socket.gethostbyname",
            return_value=MOCK_IPS["fritz.box"],
        ),
    ):
        mock_request_get.return_value.status_code = 200
        mock_request_get.return_value.content = MOCK_REQUEST
        mock_request_post.return_value.status_code = 200
        mock_request_post.return_value.text = MOCK_REQUEST

        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": SOURCE_USER,
                "show_advanced_options": show_advanced_options,
            },
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input=user_input
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"] == expected_config
        assert (
            result["options"][CONF_CONSIDER_HOME]
            == DEFAULT_CONSIDER_HOME.total_seconds()
        )
        assert not result["result"].unique_id

    assert mock_setup_entry.called


@pytest.mark.parametrize(
    ("show_advanced_options", "user_input"),
    [(True, MOCK_USER_INPUT_ADVANCED), (False, MOCK_USER_INPUT_SIMPLE)],
)
async def test_user_already_configured(
    menuai: menuai,
    fc_class_mock,
    show_advanced_options: bool,
    user_input,
) -> None:
    """Test starting a flow by user with an already configured device."""

    mock_config = MockConfigEntry(domain=DOMAIN, data=user_input)
    mock_config.add_to_menuai(menuai)

    with (
        patch(
            "menuai.components.fritz.config_flow.FritzConnection",
            side_effect=fc_class_mock,
        ),
        patch(
            "menuai.components.fritz.coordinator.FritzBoxTools._update_device_info",
            return_value=MOCK_FIRMWARE_INFO,
        ),
        patch(
            "requests.get",
        ) as mock_request_get,
        patch(
            "requests.post",
        ) as mock_request_post,
        patch(
            "menuai.components.fritz.config_flow.socket.gethostbyname",
            return_value=MOCK_IPS["fritz.box"],
        ),
    ):
        mock_request_get.return_value.status_code = 200
        mock_request_get.return_value.content = MOCK_REQUEST
        mock_request_post.return_value.status_code = 200
        mock_request_post.return_value.text = MOCK_REQUEST

        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": SOURCE_USER,
                "show_advanced_options": show_advanced_options,
            },
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input=MOCK_USER_INPUT_SIMPLE
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"]["base"] == "already_configured"


@pytest.mark.parametrize(
    "error",
    FRITZ_AUTH_EXCEPTIONS,
)
@pytest.mark.parametrize(
    ("show_advanced_options", "user_input"),
    [(True, MOCK_USER_INPUT_ADVANCED), (False, MOCK_USER_INPUT_SIMPLE)],
)
async def test_exception_security(
    menuai: menuai,
    error,
    show_advanced_options: bool,
    user_input,
) -> None:
    """Test starting a flow by user with invalid credentials."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER, "show_advanced_options": show_advanced_options},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "menuai.components.fritz.config_flow.FritzConnection",
        side_effect=error,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input=user_input
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"]["base"] == ERROR_AUTH_INVALID


@pytest.mark.parametrize(
    ("show_advanced_options", "user_input"),
    [(True, MOCK_USER_INPUT_ADVANCED), (False, MOCK_USER_INPUT_SIMPLE)],
)
async def test_exception_connection(
    menuai: menuai,
    show_advanced_options: bool,
    user_input,
) -> None:
    """Test starting a flow by user with a connection error."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER, "show_advanced_options": show_advanced_options},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "menuai.components.fritz.config_flow.FritzConnection",
        side_effect=FritzConnectionException,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input=user_input
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"]["base"] == ERROR_CANNOT_CONNECT


@pytest.mark.parametrize(
    ("show_advanced_options", "user_input"),
    [(True, MOCK_USER_INPUT_ADVANCED), (False, MOCK_USER_INPUT_SIMPLE)],
)
async def test_exception_unknown(
    menuai: menuai, show_advanced_options: bool, user_input
) -> None:
    """Test starting a flow by user with an unknown exception."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER, "show_advanced_options": show_advanced_options},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "menuai.components.fritz.config_flow.FritzConnection",
        side_effect=OSError,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input=user_input
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"]["base"] == ERROR_UNKNOWN


async def test_reauth_successful(
    menuai: menuai,
    fc_class_mock,
) -> None:
    """Test starting a reauthentication flow."""

    mock_config = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_DATA)
    mock_config.add_to_menuai(menuai)
    result = await mock_config.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    with (
        patch(
            "menuai.components.fritz.config_flow.FritzConnection",
            side_effect=fc_class_mock,
        ),
        patch(
            "menuai.components.fritz.coordinator.FritzBoxTools._update_device_info",
            return_value=MOCK_FIRMWARE_INFO,
        ),
        patch(
            "menuai.components.fritz.async_setup_entry",
        ) as mock_setup_entry,
        patch(
            "requests.get",
        ) as mock_request_get,
        patch(
            "requests.post",
        ) as mock_request_post,
    ):
        mock_request_get.return_value.status_code = 200
        mock_request_get.return_value.content = MOCK_REQUEST
        mock_request_post.return_value.status_code = 200
        mock_request_post.return_value.text = MOCK_REQUEST

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_USERNAME: "other_fake_user",
                CONF_PASSWORD: "other_fake_password",
            },
        )

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "reauth_successful"

    assert mock_setup_entry.called


@pytest.mark.parametrize(
    ("side_effect", "error"),
    [
        (FritzAuthorizationError, ERROR_AUTH_INVALID),
        (FritzConnectionException, ERROR_CANNOT_CONNECT),
        (FritzSecurityError, ERROR_AUTH_INVALID),
    ],
)
async def test_reauth_not_successful(
    menuai: menuai,
    fc_class_mock,
    side_effect,
    error,
) -> None:
    """Test starting a reauthentication flow but no connection found."""

    mock_config = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_DATA)
    mock_config.add_to_menuai(menuai)
    result = await mock_config.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    with patch(
        "menuai.components.fritz.config_flow.FritzConnection",
        side_effect=side_effect,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_USERNAME: "other_fake_user",
                CONF_PASSWORD: "other_fake_password",
            },
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"
        assert result["errors"]["base"] == error


@pytest.mark.parametrize(
    ("show_advanced_options", "user_input", "expected_config"),
    [
        (
            True,
            {CONF_HOST: "host_a", CONF_PORT: 49000, CONF_SSL: False},
            {CONF_HOST: "host_a", CONF_PORT: 49000, CONF_SSL: False},
        ),
        (
            True,
            {CONF_HOST: "host_a", CONF_PORT: 49443, CONF_SSL: True},
            {CONF_HOST: "host_a", CONF_PORT: 49443, CONF_SSL: True},
        ),
        (
            True,
            {CONF_HOST: "host_a", CONF_PORT: 12345, CONF_SSL: True},
            {CONF_HOST: "host_a", CONF_PORT: 12345, CONF_SSL: True},
        ),
        (
            False,
            {CONF_HOST: "host_b", CONF_SSL: False},
            {CONF_HOST: "host_b", CONF_PORT: 49000, CONF_SSL: False},
        ),
        (
            False,
            {CONF_HOST: "host_b", CONF_SSL: True},
            {CONF_HOST: "host_b", CONF_PORT: 49443, CONF_SSL: True},
        ),
    ],
)
async def test_reconfigure_successful(
    menuai: menuai,
    fc_class_mock,
    show_advanced_options: bool,
    user_input: dict,
    expected_config: dict,
) -> None:
    """Test starting a reconfigure flow."""

    mock_config = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_DATA)
    mock_config.add_to_menuai(menuai)

    with (
        patch(
            "menuai.components.fritz.config_flow.FritzConnection",
            side_effect=fc_class_mock,
        ),
        patch(
            "menuai.components.fritz.coordinator.FritzBoxTools._update_device_info",
            return_value=MOCK_FIRMWARE_INFO,
        ),
        patch(
            "menuai.components.fritz.async_setup_entry",
        ) as mock_setup_entry,
        patch(
            "requests.get",
        ) as mock_request_get,
        patch(
            "requests.post",
        ) as mock_request_post,
    ):
        mock_request_get.return_value.status_code = 200
        mock_request_get.return_value.content = MOCK_REQUEST
        mock_request_post.return_value.status_code = 200
        mock_request_post.return_value.text = MOCK_REQUEST

        result = await mock_config.start_reconfigure_flow(
            menuai,
            show_advanced_options=show_advanced_options,
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "reconfigure"

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=user_input,
        )

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "reconfigure_successful"
        assert mock_config.data == {
            **expected_config,
            CONF_USERNAME: "fake_user",
            CONF_PASSWORD: "fake_pass",
        }

    assert mock_setup_entry.called


async def test_reconfigure_not_successful(
    menuai: menuai,
    fc_class_mock,
) -> None:
    """Test starting a reconfigure flow but no connection found."""

    mock_config = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_DATA)
    mock_config.add_to_menuai(menuai)

    with (
        patch(
            "menuai.components.fritz.config_flow.FritzConnection",
            side_effect=[FritzConnectionException, fc_class_mock],
        ),
        patch(
            "menuai.components.fritz.coordinator.FritzBoxTools._update_device_info",
            return_value=MOCK_FIRMWARE_INFO,
        ),
        patch(
            "menuai.components.fritz.async_setup_entry",
        ),
        patch(
            "requests.get",
        ) as mock_request_get,
        patch(
            "requests.post",
        ) as mock_request_post,
    ):
        mock_request_get.return_value.status_code = 200
        mock_request_get.return_value.content = MOCK_REQUEST
        mock_request_post.return_value.status_code = 200
        mock_request_post.return_value.text = MOCK_REQUEST

        result = await mock_config.start_reconfigure_flow(menuai)

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "reconfigure"

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "fake_host",
                CONF_SSL: False,
            },
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "reconfigure"
        assert result["errors"]["base"] == ERROR_CANNOT_CONNECT

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "fake_host",
                CONF_SSL: False,
            },
        )

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "reconfigure_successful"
        assert mock_config.data == {
            CONF_HOST: "fake_host",
            CONF_PASSWORD: "fake_pass",
            CONF_USERNAME: "fake_user",
            CONF_PORT: 49000,
            CONF_SSL: False,
        }


async def test_ssdp_already_configured(menuai: menuai, fc_class_mock) -> None:
    """Test starting a flow from discovery with an already configured device."""

    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_USER_DATA,
        unique_id="only-a-test",
    )
    mock_config.add_to_menuai(menuai)

    with (
        patch(
            "menuai.components.fritz.config_flow.FritzConnection",
            side_effect=fc_class_mock,
        ),
        patch(
            "menuai.components.fritz.config_flow.socket.gethostbyname",
            return_value=MOCK_IPS["fritz.box"],
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_SSDP}, data=MOCK_SSDP_DATA
        )
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"


async def test_ssdp_already_configured_host(menuai: menuai, fc_class_mock) -> None:
    """Test starting a flow from discovery with an already configured host."""

    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_USER_DATA,
        unique_id="different-test",
    )
    mock_config.add_to_menuai(menuai)

    with (
        patch(
            "menuai.components.fritz.config_flow.FritzConnection",
            side_effect=fc_class_mock,
        ),
        patch(
            "menuai.components.fritz.config_flow.socket.gethostbyname",
            return_value=MOCK_IPS["fritz.box"],
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_SSDP}, data=MOCK_SSDP_DATA
        )
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"


async def test_ssdp_already_configured_host_uuid(
    menuai: menuai, fc_class_mock
) -> None:
    """Test starting a flow from discovery with an already configured uuid."""

    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_USER_DATA,
        unique_id=None,
    )
    mock_config.add_to_menuai(menuai)

    with (
        patch(
            "menuai.components.fritz.config_flow.FritzConnection",
            side_effect=fc_class_mock,
        ),
        patch(
            "menuai.components.fritz.config_flow.socket.gethostbyname",
            return_value=MOCK_IPS["fritz.box"],
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_SSDP}, data=MOCK_SSDP_DATA
        )
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"


async def test_ssdp_already_in_progress_host(
    menuai: menuai, fc_class_mock
) -> None:
    """Test starting a flow from discovery twice."""
    with patch(
        "menuai.components.fritz.config_flow.FritzConnection",
        side_effect=fc_class_mock,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_SSDP}, data=MOCK_SSDP_DATA
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "confirm"

        MOCK_NO_UNIQUE_ID = dataclasses.replace(MOCK_SSDP_DATA)
        MOCK_NO_UNIQUE_ID.upnp = MOCK_NO_UNIQUE_ID.upnp.copy()
        del MOCK_NO_UNIQUE_ID.upnp[ATTR_UPNP_UDN]
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_SSDP}, data=MOCK_NO_UNIQUE_ID
        )
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_in_progress"


async def test_ssdp(menuai: menuai, fc_class_mock) -> None:
    """Test starting a flow from discovery."""
    with (
        patch(
            "menuai.components.fritz.config_flow.FritzConnection",
            side_effect=fc_class_mock,
        ),
        patch(
            "menuai.components.fritz.coordinator.FritzBoxTools._update_device_info",
            return_value=MOCK_FIRMWARE_INFO,
        ),
        patch("menuai.components.fritz.async_setup_entry") as mock_setup_entry,
        patch("requests.get") as mock_request_get,
        patch("requests.post") as mock_request_post,
    ):
        mock_request_get.return_value.status_code = 200
        mock_request_get.return_value.content = MOCK_REQUEST
        mock_request_post.return_value.status_code = 200
        mock_request_post.return_value.text = MOCK_REQUEST

        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_SSDP}, data=MOCK_SSDP_DATA
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "confirm"

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_USERNAME: "fake_user",
                CONF_PASSWORD: "fake_pass",
            },
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_HOST] == MOCK_IPS["fritz.box"]
        assert result["data"][CONF_PASSWORD] == "fake_pass"
        assert result["data"][CONF_USERNAME] == "fake_user"

    assert mock_setup_entry.called


async def test_ssdp_exception(menuai: menuai) -> None:
    """Test starting a flow from discovery but no device found."""
    with patch(
        "menuai.components.fritz.config_flow.FritzConnection",
        side_effect=FritzConnectionException,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_SSDP}, data=MOCK_SSDP_DATA
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "confirm"

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_USERNAME: "fake_user",
                CONF_PASSWORD: "fake_pass",
            },
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "confirm"


async def test_options_flow(menuai: menuai) -> None:
    """Test options flow."""

    mock_config = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_DATA)
    mock_config.add_to_menuai(menuai)

    result = await menuai.config_entries.options.async_init(mock_config.entry_id)
    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_CONSIDER_HOME: 37,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_OLD_DISCOVERY: False,
        CONF_CONSIDER_HOME: 37,
        CONF_FEATURE_DEVICE_TRACKING: True,
    }


async def test_ssdp_ipv6_link_local(menuai: menuai) -> None:
    """Test ignoring ipv6-link-local while ssdp discovery."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_SSDP},
        data=SsdpServiceInfo(
            ssdp_usn="mock_usn",
            ssdp_st="mock_st",
            ssdp_location="https://[fe80::1ff:fe23:4567:890a]:12345/test",
            upnp={
                ATTR_UPNP_FRIENDLY_NAME: "fake_name",
                ATTR_UPNP_UDN: "uuid:only-a-test",
            },
        ),
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "ignore_ip6_link_local"


async def test_upnp_not_enabled(menuai: menuai) -> None:
    """Test if UPNP service is enabled on the router."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    # Disable UPnP
    services = deepcopy(MOCK_FB_SERVICES)
    services["X_AVM-DE_UPnP1"]["GetInfo"]["NewEnable"] = False

    with patch(
        "menuai.components.fritz.config_flow.FritzConnection",
        return_value=FritzConnectionMock(services),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input=MOCK_USER_INPUT_SIMPLE
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"]["base"] == ERROR_UPNP_NOT_CONFIGURED

    # Enable UPnP
    services["X_AVM-DE_UPnP1"]["GetInfo"]["NewEnable"] = True

    with (
        patch(
            "menuai.components.fritz.config_flow.FritzConnection",
            return_value=FritzConnectionMock(services),
        ),
        patch(
            "menuai.components.fritz.config_flow.socket.gethostbyname",
            return_value=MOCK_IPS["fritz.box"],
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input=MOCK_USER_INPUT_SIMPLE
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_HOST] == "fake_host"
        assert result["data"][CONF_PASSWORD] == "fake_pass"
        assert result["data"][CONF_USERNAME] == "fake_user"
        assert result["data"][CONF_PORT] == 49000
        assert result["data"][CONF_SSL] is False
