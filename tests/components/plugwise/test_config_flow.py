"""Test the Plugwise config flow."""

from ipaddress import ip_address
from unittest.mock import AsyncMock, MagicMock

from plugwise.exceptions import (
    ConnectionFailedError,
    InvalidAuthentication,
    InvalidSetupError,
    InvalidXMLError,
    UnsupportedDeviceError,
)
import pytest

from menuai.components.plugwise.const import DEFAULT_PORT, DOMAIN
from menuai.config_entries import SOURCE_USER, SOURCE_ZEROCONF, ConfigFlowResult
from menuai.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SOURCE,
    CONF_USERNAME,
)
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers.service_info.zeroconf import ZeroconfServiceInfo

from tests.common import MockConfigEntry

TEST_HOST = "1.1.1.1"
TEST_HOSTNAME = "smileabcdef"
TEST_HOSTNAME2 = "stretchabc"
TEST_PASSWORD = "test_password"
TEST_PORT = 81
TEST_USERNAME = "smile"
TEST_USERNAME2 = "stretch"
TEST_SMILE_HOST = "smile12345"

TEST_DISCOVERY = ZeroconfServiceInfo(
    ip_address=ip_address(TEST_HOST),
    ip_addresses=[ip_address(TEST_HOST)],
    # The added `-2` is to simulate mDNS collision
    hostname=f"{TEST_HOSTNAME}-2.local.",
    name="mock_name",
    port=DEFAULT_PORT,
    properties={
        "product": "smile",
        "version": "1.2.3",
        "hostname": f"{TEST_HOSTNAME}.local.",
    },
    type="mock_type",
)

TEST_DISCOVERY2 = ZeroconfServiceInfo(
    ip_address=ip_address(TEST_HOST),
    ip_addresses=[ip_address(TEST_HOST)],
    hostname=f"{TEST_HOSTNAME2}.local.",
    name="mock_name",
    port=DEFAULT_PORT,
    properties={
        "product": "stretch",
        "version": "1.2.3",
        "hostname": f"{TEST_HOSTNAME2}.local.",
    },
    type="mock_type",
)

TEST_DISCOVERY_ANNA = ZeroconfServiceInfo(
    ip_address=ip_address(TEST_HOST),
    ip_addresses=[ip_address(TEST_HOST)],
    hostname=f"{TEST_HOSTNAME}.local.",
    name="mock_name",
    port=DEFAULT_PORT,
    properties={
        "product": "smile_thermo",
        "version": "1.2.3",
        "hostname": f"{TEST_HOSTNAME}.local.",
    },
    type="mock_type",
)

TEST_DISCOVERY_ADAM = ZeroconfServiceInfo(
    ip_address=ip_address(TEST_HOST),
    ip_addresses=[ip_address(TEST_HOST)],
    hostname=f"{TEST_HOSTNAME2}.local.",
    name="mock_name",
    port=DEFAULT_PORT,
    properties={
        "product": "smile_open_therm",
        "version": "1.2.3",
        "hostname": f"{TEST_HOSTNAME2}.local.",
    },
    type="mock_type",
)


async def test_form(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
    mock_smile_config_flow: MagicMock,
) -> None:
    """Test the full user configuration flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={CONF_SOURCE: SOURCE_USER}
    )
    assert result.get("type") is FlowResultType.FORM
    assert result.get("errors") == {}
    assert result.get("step_id") == "user"

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: TEST_HOST,
            CONF_PASSWORD: TEST_PASSWORD,
        },
    )
    await menuai.async_block_till_done()

    assert result2.get("type") is FlowResultType.CREATE_ENTRY
    assert result2.get("title") == "Test Smile Name"
    assert result2.get("data") == {
        CONF_HOST: TEST_HOST,
        CONF_PASSWORD: TEST_PASSWORD,
        CONF_PORT: DEFAULT_PORT,
        CONF_USERNAME: TEST_USERNAME,
    }

    assert len(mock_setup_entry.mock_calls) == 1
    assert len(mock_smile_config_flow.connect.mock_calls) == 1

    assert result2["result"].unique_id == TEST_SMILE_HOST


@pytest.mark.parametrize(
    ("discovery", "username"),
    [
        (TEST_DISCOVERY, TEST_USERNAME),
        (TEST_DISCOVERY2, TEST_USERNAME2),
    ],
)
async def test_zeroconf_flow(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
    mock_smile_config_flow: MagicMock,
    discovery: ZeroconfServiceInfo,
    username: str,
) -> None:
    """Test config flow for smile devices."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_ZEROCONF},
        data=TEST_DISCOVERY,
    )
    assert result.get("type") is FlowResultType.FORM
    assert result.get("errors") == {}
    assert result.get("step_id") == "user"
    assert "flow_id" in result

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_PASSWORD: TEST_PASSWORD},
    )
    await menuai.async_block_till_done()

    assert result2.get("type") is FlowResultType.CREATE_ENTRY
    assert result2.get("title") == "Test Smile Name"
    assert result2.get("data") == {
        CONF_HOST: TEST_HOST,
        CONF_PASSWORD: TEST_PASSWORD,
        CONF_PORT: DEFAULT_PORT,
        CONF_USERNAME: TEST_USERNAME,
    }

    assert len(mock_setup_entry.mock_calls) == 1
    assert len(mock_smile_config_flow.connect.mock_calls) == 1

    assert result2["result"].unique_id == TEST_SMILE_HOST


async def test_zeroconf_flow_stretch(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
    mock_smile_config_flow: MagicMock,
) -> None:
    """Test config flow for stretch devices."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_ZEROCONF},
        data=TEST_DISCOVERY2,
    )
    assert result.get("type") is FlowResultType.FORM
    assert result.get("errors") == {}
    assert result.get("step_id") == "user"
    assert "flow_id" in result

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_PASSWORD: TEST_PASSWORD},
    )
    await menuai.async_block_till_done()

    assert result2.get("type") is FlowResultType.CREATE_ENTRY
    assert result2.get("title") == "Test Smile Name"
    assert result2.get("data") == {
        CONF_HOST: TEST_HOST,
        CONF_PASSWORD: TEST_PASSWORD,
        CONF_PORT: DEFAULT_PORT,
        CONF_USERNAME: TEST_USERNAME2,
    }

    assert len(mock_setup_entry.mock_calls) == 1
    assert len(mock_smile_config_flow.connect.mock_calls) == 1


async def test_zercoconf_discovery_update_configuration(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
    mock_smile_config_flow: MagicMock,
) -> None:
    """Test if a discovered device is configured and updated with new host."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=CONF_NAME,
        data={
            CONF_HOST: "0.0.0.0",
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
        },
        unique_id=TEST_HOSTNAME,
    )
    entry.add_to_menuai(menuai)

    assert entry.data[CONF_HOST] == "0.0.0.0"

    # Test that an invalid discovery doesn't update the entry
    mock_smile_config_flow.connect.side_effect = ConnectionFailedError
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_ZEROCONF},
        data=TEST_DISCOVERY,
    )
    assert result.get("type") is FlowResultType.ABORT
    assert result.get("reason") == "already_configured"
    assert entry.data[CONF_HOST] == "0.0.0.0"

    mock_smile_config_flow.connect.side_effect = None
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_ZEROCONF},
        data=TEST_DISCOVERY,
    )

    assert result.get("type") is FlowResultType.ABORT
    assert result.get("reason") == "already_configured"
    assert entry.data[CONF_HOST] == "1.1.1.1"


@pytest.mark.parametrize(
    ("side_effect", "reason"),
    [
        (ConnectionFailedError, "cannot_connect"),
        (InvalidAuthentication, "invalid_auth"),
        (InvalidSetupError, "invalid_setup"),
        (InvalidXMLError, "response_error"),
        (RuntimeError, "unknown"),
        (UnsupportedDeviceError, "unsupported"),
    ],
)
async def test_flow_errors(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
    mock_smile_config_flow: MagicMock,
    side_effect: Exception,
    reason: str,
) -> None:
    """Test we handle each exception error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_USER},
    )
    assert result.get("type") is FlowResultType.FORM
    assert result.get("errors") == {}
    assert result.get("step_id") == "user"
    assert "flow_id" in result

    mock_smile_config_flow.connect.side_effect = side_effect

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_HOST: TEST_HOST, CONF_PASSWORD: TEST_PASSWORD},
    )

    assert result2.get("type") is FlowResultType.FORM
    assert result2.get("errors") == {"base": reason}
    assert result2.get("step_id") == "user"

    assert len(mock_setup_entry.mock_calls) == 0
    assert len(mock_smile_config_flow.connect.mock_calls) == 1

    mock_smile_config_flow.connect.side_effect = None
    result3 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_HOST: TEST_HOST, CONF_PASSWORD: TEST_PASSWORD},
    )

    assert result3.get("type") is FlowResultType.CREATE_ENTRY
    assert result3.get("title") == "Test Smile Name"
    assert result3.get("data") == {
        CONF_HOST: TEST_HOST,
        CONF_PASSWORD: TEST_PASSWORD,
        CONF_PORT: DEFAULT_PORT,
        CONF_USERNAME: TEST_USERNAME,
    }

    assert len(mock_setup_entry.mock_calls) == 1
    assert len(mock_smile_config_flow.connect.mock_calls) == 2


async def test_user_abort_existing_anna(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
    mock_smile_config_flow: MagicMock,
) -> None:
    """Test the full user configuration flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=CONF_NAME,
        data={
            CONF_HOST: TEST_HOST,
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
        },
        unique_id=TEST_SMILE_HOST,
    )
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={CONF_SOURCE: SOURCE_USER}
    )

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: TEST_HOST,
            CONF_PASSWORD: TEST_PASSWORD,
        },
    )
    await menuai.async_block_till_done()

    assert result2.get("type") is FlowResultType.ABORT
    assert result2.get("reason") == "already_configured"


async def test_zeroconf_abort_existing_anna(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
    mock_smile_config_flow: MagicMock,
) -> None:
    """Test the full user configuration flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=CONF_NAME,
        data={
            CONF_HOST: TEST_HOST,
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
        },
        unique_id=TEST_HOSTNAME,
    )
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_ZEROCONF},
        data=TEST_DISCOVERY_ANNA,
    )

    assert result.get("type") is FlowResultType.ABORT
    assert result.get("reason") == "already_configured"


async def test_zeroconf_abort_anna_with_existing_config_entries(
    menuai: menuai,
    mock_smile_adam: MagicMock,
    init_integration: MockConfigEntry,
) -> None:
    """Test we abort Anna discovery with existing config entries."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_ZEROCONF},
        data=TEST_DISCOVERY_ANNA,
    )
    assert result.get("type") is FlowResultType.ABORT
    assert result.get("reason") == "anna_with_adam"


async def test_zeroconf_abort_anna_with_adam(menuai: menuai) -> None:
    """Test we abort Anna discovery when an Adam is also discovered."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_ZEROCONF},
        data=TEST_DISCOVERY_ANNA,
    )
    assert result.get("type") is FlowResultType.FORM
    assert result.get("step_id") == "user"

    flows_in_progress = menuai.config_entries.flow._handler_progress_index[DOMAIN]
    assert len(flows_in_progress) == 1
    assert list(flows_in_progress)[0].product == "smile_thermo"

    # Discover Adam, Anna should be aborted and no longer present
    result2 = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_ZEROCONF},
        data=TEST_DISCOVERY_ADAM,
    )

    assert result2.get("type") is FlowResultType.FORM
    assert result2.get("step_id") == "user"

    flows_in_progress = menuai.config_entries.flow._handler_progress_index[DOMAIN]
    assert len(flows_in_progress) == 1
    assert list(flows_in_progress)[0].product == "smile_open_therm"

    # Discover Anna again, Anna should be aborted directly
    result3 = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_ZEROCONF},
        data=TEST_DISCOVERY_ANNA,
    )
    assert result3.get("type") is FlowResultType.ABORT
    assert result3.get("reason") == "anna_with_adam"

    # Adam should still be there
    flows_in_progress = menuai.config_entries.flow._handler_progress_index[DOMAIN]
    assert len(flows_in_progress) == 1
    assert list(flows_in_progress)[0].product == "smile_open_therm"


async def _start_reconfigure_flow(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    host_ip: str,
) -> ConfigFlowResult:
    """Initialize a reconfigure flow."""
    mock_config_entry.add_to_menuai(menuai)

    reconfigure_result = await mock_config_entry.start_reconfigure_flow(menuai)

    assert reconfigure_result["type"] is FlowResultType.FORM
    assert reconfigure_result["step_id"] == "reconfigure"

    return await menuai.config_entries.flow.async_configure(
        reconfigure_result["flow_id"], {CONF_HOST: host_ip}
    )


async def test_reconfigure_flow(
    menuai: menuai,
    mock_smile_adam: AsyncMock,
    mock_setup_entry: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test reconfigure flow."""
    result = await _start_reconfigure_flow(menuai, mock_config_entry, TEST_HOST)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"

    assert mock_config_entry.data.get(CONF_HOST) == TEST_HOST


async def test_reconfigure_flow_smile_mismatch(
    menuai: menuai,
    mock_smile_adam: AsyncMock,
    mock_setup_entry: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test reconfigure flow aborts on other Smile ID."""
    mock_smile_adam.smile_hostname = TEST_SMILE_HOST

    result = await _start_reconfigure_flow(menuai, mock_config_entry, TEST_HOST)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_the_same_smile"


@pytest.mark.parametrize(
    ("side_effect", "reason"),
    [
        (ConnectionFailedError, "cannot_connect"),
        (InvalidAuthentication, "invalid_auth"),
        (InvalidSetupError, "invalid_setup"),
        (InvalidXMLError, "response_error"),
        (RuntimeError, "unknown"),
        (UnsupportedDeviceError, "unsupported"),
    ],
)
async def test_reconfigure_flow_connect_errors(
    menuai: menuai,
    mock_smile_adam: AsyncMock,
    mock_config_entry: MockConfigEntry,
    side_effect: Exception,
    reason: str,
) -> None:
    """Test we handle each reconfigure exception error and recover."""

    mock_smile_adam.connect.side_effect = side_effect

    result = await _start_reconfigure_flow(menuai, mock_config_entry, TEST_HOST)

    assert result.get("type") is FlowResultType.FORM
    assert result.get("errors") == {"base": reason}
    assert result.get("step_id") == "reconfigure"

    mock_smile_adam.connect.side_effect = None

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: TEST_HOST}
    )

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "reconfigure_successful"

    assert mock_config_entry.data.get(CONF_HOST) == TEST_HOST
