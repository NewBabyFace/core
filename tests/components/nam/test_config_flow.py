"""Define tests for the Nettigo Air Monitor config flow."""

from ipaddress import ip_address
from unittest.mock import patch

from nettigo_air_monitor import ApiError, AuthFailedError, CannotGetMacError
import pytest

from menuai.components.nam.const import DOMAIN
from menuai.config_entries import SOURCE_USER, SOURCE_ZEROCONF
from menuai.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers.service_info.zeroconf import ZeroconfServiceInfo

from tests.common import MockConfigEntry

DISCOVERY_INFO = ZeroconfServiceInfo(
    ip_address=ip_address("10.10.2.3"),
    ip_addresses=[ip_address("10.10.2.3")],
    hostname="mock_hostname",
    name="mock_name",
    port=None,
    properties={},
    type="mock_type",
)
VALID_CONFIG = {"host": "10.10.2.3"}
VALID_AUTH = {"username": "fake_username", "password": "fake_password"}
DEVICE_CONFIG = {"www_basicauth_enabled": False}
DEVICE_CONFIG_AUTH = {"www_basicauth_enabled": True}


async def test_form_create_entry_without_auth(menuai: menuai) -> None:
    """Test that the user step without auth works."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.nam.NettigoAirMonitor.async_check_credentials",
            return_value=DEVICE_CONFIG,
        ),
        patch(
            "menuai.components.nam.NettigoAirMonitor.async_get_mac_address",
            return_value="aa:bb:cc:dd:ee:ff",
        ),
        patch(
            "menuai.components.nam.async_setup_entry", return_value=True
        ) as mock_setup_entry,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            VALID_CONFIG,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "10.10.2.3"
    assert result["data"]["host"] == "10.10.2.3"
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_create_entry_with_auth(menuai: menuai) -> None:
    """Test that the user step with auth works."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.nam.NettigoAirMonitor.async_check_credentials",
            return_value=DEVICE_CONFIG_AUTH,
        ),
        patch(
            "menuai.components.nam.NettigoAirMonitor.async_get_mac_address",
            return_value="aa:bb:cc:dd:ee:ff",
        ),
        patch(
            "menuai.components.nam.async_setup_entry", return_value=True
        ) as mock_setup_entry,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            VALID_CONFIG,
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "credentials"

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            VALID_AUTH,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "10.10.2.3"
    assert result["data"]["host"] == "10.10.2.3"
    assert result["data"]["username"] == "fake_username"
    assert result["data"]["password"] == "fake_password"
    assert len(mock_setup_entry.mock_calls) == 1


async def test_reauth_successful(menuai: menuai) -> None:
    """Test starting a reauthentication flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="10.10.2.3",
        unique_id="aa:bb:cc:dd:ee:ff",
        data={"host": "10.10.2.3"},
    )
    entry.add_to_menuai(menuai)
    result = await entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    with (
        patch(
            "menuai.components.nam.NettigoAirMonitor.async_check_credentials",
            return_value=DEVICE_CONFIG_AUTH,
        ),
        patch(
            "menuai.components.nam.NettigoAirMonitor.async_get_mac_address",
            return_value="aa:bb:cc:dd:ee:ff",
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=VALID_AUTH,
        )

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "reauth_successful"


async def test_reauth_unsuccessful(menuai: menuai) -> None:
    """Test starting a reauthentication flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="10.10.2.3",
        unique_id="aa:bb:cc:dd:ee:ff",
        data={"host": "10.10.2.3"},
    )
    entry.add_to_menuai(menuai)
    result = await entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    with patch(
        "menuai.components.nam.NettigoAirMonitor.async_check_credentials",
        side_effect=ApiError("API Error"),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=VALID_AUTH,
        )

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "reauth_unsuccessful"


@pytest.mark.parametrize(
    "error",
    [
        (ApiError("API Error"), "cannot_connect"),
        (AuthFailedError("Auth Error"), "invalid_auth"),
        (TimeoutError, "cannot_connect"),
        (ValueError, "unknown"),
    ],
)
async def test_form_with_auth_errors(menuai: menuai, error) -> None:
    """Test we handle errors when auth is required."""
    exc, base_error = error
    with (
        patch(
            "menuai.components.nam.NettigoAirMonitor.async_check_credentials",
            side_effect=AuthFailedError("Auth Error"),
        ),
        patch(
            "menuai.components.nam.NettigoAirMonitor.async_get_mac_address",
            return_value="aa:bb:cc:dd:ee:ff",
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data=VALID_CONFIG,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "credentials"

    with patch(
        "menuai.components.nam.NettigoAirMonitor.initialize",
        side_effect=exc,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            VALID_AUTH,
        )

    assert result["errors"] == {"base": base_error}


@pytest.mark.parametrize(
    "error",
    [
        (ApiError("API Error"), "cannot_connect"),
        (TimeoutError, "cannot_connect"),
        (ValueError, "unknown"),
    ],
)
async def test_form_errors(menuai: menuai, error) -> None:
    """Test we handle errors."""
    exc, base_error = error
    with patch(
        "menuai.components.nam.NettigoAirMonitor.initialize",
        side_effect=exc,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data=VALID_CONFIG,
        )

    assert result["errors"] == {"base": base_error}


async def test_form_abort(menuai: menuai) -> None:
    """Test we handle abort after error."""
    with (
        patch(
            "menuai.components.nam.NettigoAirMonitor.async_check_credentials",
            return_value=DEVICE_CONFIG,
        ),
        patch(
            "menuai.components.nam.NettigoAirMonitor.async_get_mac_address",
            side_effect=CannotGetMacError("Cannot get MAC address from device"),
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data=VALID_CONFIG,
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "device_unsupported"


async def test_form_already_configured(menuai: menuai) -> None:
    """Test that errors are shown when duplicates are added."""
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="aa:bb:cc:dd:ee:ff", data=VALID_CONFIG
    )
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with (
        patch(
            "menuai.components.nam.NettigoAirMonitor.async_check_credentials",
            return_value=DEVICE_CONFIG,
        ),
        patch(
            "menuai.components.nam.NettigoAirMonitor.async_get_mac_address",
            return_value="aa:bb:cc:dd:ee:ff",
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {"host": "1.1.1.1"},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"

    # Test config entry got updated with latest IP
    assert entry.data["host"] == "1.1.1.1"


async def test_zeroconf(menuai: menuai) -> None:
    """Test we get the form."""
    with (
        patch(
            "menuai.components.nam.NettigoAirMonitor.async_check_credentials",
            return_value=DEVICE_CONFIG,
        ),
        patch(
            "menuai.components.nam.NettigoAirMonitor.async_get_mac_address",
            return_value="aa:bb:cc:dd:ee:ff",
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            data=DISCOVERY_INFO,
            context={"source": SOURCE_ZEROCONF},
        )
        context = next(
            flow["context"]
            for flow in menuai.config_entries.flow.async_progress()
            if flow["flow_id"] == result["flow_id"]
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}
    assert context["title_placeholders"]["host"] == "10.10.2.3"
    assert context["confirm_only"] is True

    with patch(
        "menuai.components.nam.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "10.10.2.3"
    assert result["data"] == {"host": "10.10.2.3"}
    assert len(mock_setup_entry.mock_calls) == 1


async def test_zeroconf_with_auth(menuai: menuai) -> None:
    """Test that the zeroconf step with auth works."""
    with (
        patch(
            "menuai.components.nam.NettigoAirMonitor.async_check_credentials",
            side_effect=AuthFailedError("Auth Error"),
        ),
        patch(
            "menuai.components.nam.NettigoAirMonitor.async_get_mac_address",
            return_value="aa:bb:cc:dd:ee:ff",
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            data=DISCOVERY_INFO,
            context={"source": SOURCE_ZEROCONF},
        )
        context = next(
            flow["context"]
            for flow in menuai.config_entries.flow.async_progress()
            if flow["flow_id"] == result["flow_id"]
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "credentials"
    assert result["errors"] == {}
    assert context["title_placeholders"]["host"] == "10.10.2.3"

    with (
        patch(
            "menuai.components.nam.NettigoAirMonitor.async_check_credentials",
            return_value=DEVICE_CONFIG_AUTH,
        ),
        patch(
            "menuai.components.nam.NettigoAirMonitor.async_get_mac_address",
            return_value="aa:bb:cc:dd:ee:ff",
        ),
        patch(
            "menuai.components.nam.async_setup_entry", return_value=True
        ) as mock_setup_entry,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            VALID_AUTH,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "10.10.2.3"
    assert result["data"]["host"] == "10.10.2.3"
    assert result["data"]["username"] == "fake_username"
    assert result["data"]["password"] == "fake_password"
    assert len(mock_setup_entry.mock_calls) == 1


async def test_zeroconf_host_already_configured(menuai: menuai) -> None:
    """Test that errors are shown when host is already configured."""
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="aa:bb:cc:dd:ee:ff", data=VALID_CONFIG
    )
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        data=DISCOVERY_INFO,
        context={"source": SOURCE_ZEROCONF},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.parametrize(
    "error",
    [
        (ApiError("API Error"), "cannot_connect"),
        (CannotGetMacError("Cannot get MAC address from device"), "device_unsupported"),
    ],
)
async def test_zeroconf_errors(menuai: menuai, error) -> None:
    """Test we handle errors."""
    exc, reason = error
    with patch(
        "menuai.components.nam.NettigoAirMonitor.initialize",
        side_effect=exc,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            data=DISCOVERY_INFO,
            context={"source": SOURCE_ZEROCONF},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == reason


async def test_reconfigure_successful(menuai: menuai) -> None:
    """Test starting a reconfigure flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="10.10.2.3",
        unique_id="aa:bb:cc:dd:ee:ff",
        data={
            CONF_HOST: "10.10.2.3",
            CONF_USERNAME: "fake_username",
            CONF_PASSWORD: "fake_password",
        },
    )
    entry.add_to_menuai(menuai)

    result = await entry.start_reconfigure_flow(menuai)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    with (
        patch(
            "menuai.components.nam.NettigoAirMonitor.async_check_credentials",
            return_value=DEVICE_CONFIG_AUTH,
        ),
        patch(
            "menuai.components.nam.NettigoAirMonitor.async_get_mac_address",
            return_value="aa:bb:cc:dd:ee:ff",
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_HOST: "10.10.10.10"},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data == {
        CONF_HOST: "10.10.10.10",
        CONF_USERNAME: "fake_username",
        CONF_PASSWORD: "fake_password",
    }


async def test_reconfigure_not_successful(menuai: menuai) -> None:
    """Test starting a reconfigure flow but no connection found."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="10.10.2.3",
        unique_id="aa:bb:cc:dd:ee:ff",
        data={
            CONF_HOST: "10.10.2.3",
            CONF_USERNAME: "fake_username",
            CONF_PASSWORD: "fake_password",
        },
    )
    entry.add_to_menuai(menuai)

    result = await entry.start_reconfigure_flow(menuai)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    with patch(
        "menuai.components.nam.NettigoAirMonitor.async_check_credentials",
        side_effect=ApiError("API Error"),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_HOST: "10.10.10.10"},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    assert result["errors"] == {"base": "cannot_connect"}

    with (
        patch(
            "menuai.components.nam.NettigoAirMonitor.async_check_credentials",
            return_value=DEVICE_CONFIG_AUTH,
        ),
        patch(
            "menuai.components.nam.NettigoAirMonitor.async_get_mac_address",
            return_value="aa:bb:cc:dd:ee:ff",
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_HOST: "10.10.10.10"},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data == {
        CONF_HOST: "10.10.10.10",
        CONF_USERNAME: "fake_username",
        CONF_PASSWORD: "fake_password",
    }


async def test_reconfigure_not_the_same_device(menuai: menuai) -> None:
    """Test starting the reconfiguration process, but with a different printer."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="10.10.2.3",
        unique_id="11:22:33:44:55:66",
        data={
            CONF_HOST: "10.10.2.3",
            CONF_USERNAME: "fake_username",
            CONF_PASSWORD: "fake_password",
        },
    )
    entry.add_to_menuai(menuai)

    result = await entry.start_reconfigure_flow(menuai)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    with (
        patch(
            "menuai.components.nam.NettigoAirMonitor.async_check_credentials",
            return_value=DEVICE_CONFIG_AUTH,
        ),
        patch(
            "menuai.components.nam.NettigoAirMonitor.async_get_mac_address",
            return_value="aa:bb:cc:dd:ee:ff",
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_HOST: "10.10.10.10"},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "another_device"
