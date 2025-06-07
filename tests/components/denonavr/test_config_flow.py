"""Test the DenonAVR config flow."""

from unittest.mock import patch

import pytest

from menuai import config_entries
from menuai.components.denonavr.config_flow import (
    CONF_MANUFACTURER,
    CONF_SERIAL_NUMBER,
    CONF_SHOW_ALL_SOURCES,
    CONF_TYPE,
    CONF_UPDATE_AUDYSSEY,
    CONF_USE_TELNET,
    CONF_ZONE2,
    CONF_ZONE3,
    DOMAIN,
    AvrTimoutError,
)
from menuai.const import CONF_HOST, CONF_MODEL
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers.service_info.ssdp import (
    ATTR_UPNP_MANUFACTURER,
    ATTR_UPNP_MODEL_NAME,
    ATTR_UPNP_SERIAL,
    SsdpServiceInfo,
)

from tests.common import MockConfigEntry

TEST_HOST = "1.2.3.4"
TEST_HOST2 = "5.6.7.8"
TEST_NAME = "Test_Receiver"
TEST_MODEL = "model5"
TEST_IGNORED_MODEL = "HEOS 7"
TEST_RECEIVER_TYPE = "avr-x"
TEST_SERIALNUMBER = "123456789"
TEST_MANUFACTURER = "Denon"
TEST_UPDATE_AUDYSSEY = False
TEST_SSDP_LOCATION = f"http://{TEST_HOST}/"
TEST_UNIQUE_ID = f"{TEST_MODEL}-{TEST_SERIALNUMBER}"
TEST_DISCOVER_1_RECEIVER = [{CONF_HOST: TEST_HOST}]
TEST_DISCOVER_2_RECEIVER = [{CONF_HOST: TEST_HOST}, {CONF_HOST: TEST_HOST2}]


@pytest.fixture(name="denonavr_connect", autouse=True)
def denonavr_connect_fixture():
    """Mock denonavr connection and entry setup."""
    with (
        patch(
            "menuai.components.denonavr.receiver.DenonAVR.async_setup",
            return_value=None,
        ),
        patch(
            "menuai.components.denonavr.receiver.DenonAVR.async_update",
            return_value=None,
        ),
        patch(
            "menuai.components.denonavr.receiver.DenonAVR.support_sound_mode",
            return_value=True,
        ),
        patch(
            "menuai.components.denonavr.receiver.DenonAVR.name",
            TEST_NAME,
        ),
        patch(
            "menuai.components.denonavr.receiver.DenonAVR.model_name",
            TEST_MODEL,
        ),
        patch(
            "menuai.components.denonavr.receiver.DenonAVR.serial_number",
            TEST_SERIALNUMBER,
        ),
        patch(
            "menuai.components.denonavr.receiver.DenonAVR.manufacturer",
            TEST_MANUFACTURER,
        ),
        patch(
            "menuai.components.denonavr.receiver.DenonAVR.receiver_type",
            TEST_RECEIVER_TYPE,
        ),
        patch(
            "menuai.components.denonavr.async_setup_entry",
            return_value=True,
        ),
    ):
        yield


async def test_config_flow_manual_host_success(menuai: menuai) -> None:
    """Successful flow manually initialized by the user.

    Host specified.
    """
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: TEST_HOST},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_NAME
    assert result["data"] == {
        CONF_HOST: TEST_HOST,
        CONF_MODEL: TEST_MODEL,
        CONF_TYPE: TEST_RECEIVER_TYPE,
        CONF_MANUFACTURER: TEST_MANUFACTURER,
        CONF_SERIAL_NUMBER: TEST_SERIALNUMBER,
    }
    assert result["options"] == {CONF_USE_TELNET: True}


async def test_config_flow_manual_discover_1_success(menuai: menuai) -> None:
    """Successful flow manually initialized by the user.

    Without the host specified and 1 receiver discovered.
    """
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    with patch(
        "menuai.components.denonavr.config_flow.denonavr.async_discover",
        return_value=TEST_DISCOVER_1_RECEIVER,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_NAME
    assert result["data"] == {
        CONF_HOST: TEST_HOST,
        CONF_MODEL: TEST_MODEL,
        CONF_TYPE: TEST_RECEIVER_TYPE,
        CONF_MANUFACTURER: TEST_MANUFACTURER,
        CONF_SERIAL_NUMBER: TEST_SERIALNUMBER,
    }
    assert result["options"] == {CONF_USE_TELNET: True}


async def test_config_flow_manual_discover_2_success(menuai: menuai) -> None:
    """Successful flow manually initialized by the user.

    Without the host specified and 2 receiver discovered.
    """
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    with patch(
        "menuai.components.denonavr.config_flow.denonavr.async_discover",
        return_value=TEST_DISCOVER_2_RECEIVER,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "select"
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {"select_host": TEST_HOST2},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_NAME
    assert result["data"] == {
        CONF_HOST: TEST_HOST2,
        CONF_MODEL: TEST_MODEL,
        CONF_TYPE: TEST_RECEIVER_TYPE,
        CONF_MANUFACTURER: TEST_MANUFACTURER,
        CONF_SERIAL_NUMBER: TEST_SERIALNUMBER,
    }
    assert result["options"] == {CONF_USE_TELNET: True}


async def test_config_flow_manual_discover_error(menuai: menuai) -> None:
    """Failed flow manually initialized by the user.

    Without the host specified and no receiver discovered.
    """
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    with patch(
        "menuai.components.denonavr.config_flow.denonavr.async_discover",
        return_value=[],
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "discovery_error"}


async def test_config_flow_manual_host_no_serial(menuai: menuai) -> None:
    """Successful flow manually initialized by the user.

    Host specified and an error getting the serial number.
    """
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    with patch(
        "menuai.components.denonavr.receiver.DenonAVR.serial_number",
        None,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: TEST_HOST},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_NAME
    assert result["data"] == {
        CONF_HOST: TEST_HOST,
        CONF_MODEL: TEST_MODEL,
        CONF_TYPE: TEST_RECEIVER_TYPE,
        CONF_MANUFACTURER: TEST_MANUFACTURER,
        CONF_SERIAL_NUMBER: None,
    }


async def test_config_flow_manual_host_connection_error(menuai: menuai) -> None:
    """Failed flow manually initialized by the user.

    Host specified and a connection error.
    """
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.denonavr.receiver.DenonAVR.async_setup",
            side_effect=AvrTimoutError("Timeout", "async_setup"),
        ),
        patch(
            "menuai.components.denonavr.receiver.DenonAVR.receiver_type",
            None,
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: TEST_HOST},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"


async def test_config_flow_manual_host_no_device_info(menuai: menuai) -> None:
    """Failed flow manually initialized by the user.

    Host specified and no device info (due to receiver power off).
    """
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    with patch(
        "menuai.components.denonavr.receiver.DenonAVR.receiver_type",
        None,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: TEST_HOST},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"


async def test_config_flow_ssdp(menuai: menuai) -> None:
    """Successful flow initialized by ssdp discovery."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_SSDP},
        data=SsdpServiceInfo(
            ssdp_usn="mock_usn",
            ssdp_st="mock_st",
            ssdp_location=TEST_SSDP_LOCATION,
            upnp={
                ATTR_UPNP_MANUFACTURER: TEST_MANUFACTURER,
                ATTR_UPNP_MODEL_NAME: TEST_MODEL,
                ATTR_UPNP_SERIAL: TEST_SERIALNUMBER,
            },
        ),
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_NAME
    assert result["data"] == {
        CONF_HOST: TEST_HOST,
        CONF_MODEL: TEST_MODEL,
        CONF_TYPE: TEST_RECEIVER_TYPE,
        CONF_MANUFACTURER: TEST_MANUFACTURER,
        CONF_SERIAL_NUMBER: TEST_SERIALNUMBER,
    }
    assert result["options"] == {CONF_USE_TELNET: True}


async def test_config_flow_ssdp_not_denon(menuai: menuai) -> None:
    """Failed flow initialized by ssdp discovery.

    Not supported manufacturer.
    """
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_SSDP},
        data=SsdpServiceInfo(
            ssdp_usn="mock_usn",
            ssdp_st="mock_st",
            ssdp_location=TEST_SSDP_LOCATION,
            upnp={
                ATTR_UPNP_MANUFACTURER: "NotSupported",
                ATTR_UPNP_MODEL_NAME: TEST_MODEL,
                ATTR_UPNP_SERIAL: TEST_SERIALNUMBER,
            },
        ),
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_denonavr_manufacturer"


async def test_config_flow_ssdp_missing_info(menuai: menuai) -> None:
    """Failed flow initialized by ssdp discovery.

    Missing information.
    """
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_SSDP},
        data=SsdpServiceInfo(
            ssdp_usn="mock_usn",
            ssdp_st="mock_st",
            ssdp_location=TEST_SSDP_LOCATION,
            upnp={
                ATTR_UPNP_MANUFACTURER: TEST_MANUFACTURER,
            },
        ),
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_denonavr_missing"


async def test_config_flow_ssdp_ignored_model(menuai: menuai) -> None:
    """Failed flow initialized by ssdp discovery.

    Model in the ignored models list.
    """
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_SSDP},
        data=SsdpServiceInfo(
            ssdp_usn="mock_usn",
            ssdp_st="mock_st",
            ssdp_location=TEST_SSDP_LOCATION,
            upnp={
                ATTR_UPNP_MANUFACTURER: TEST_MANUFACTURER,
                ATTR_UPNP_MODEL_NAME: TEST_IGNORED_MODEL,
                ATTR_UPNP_SERIAL: TEST_SERIALNUMBER,
            },
        ),
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_denonavr_manufacturer"


async def test_options_flow(menuai: menuai) -> None:
    """Test specifying non default settings using options flow."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=TEST_UNIQUE_ID,
        data={
            CONF_HOST: TEST_HOST,
            CONF_MODEL: TEST_MODEL,
            CONF_TYPE: TEST_RECEIVER_TYPE,
            CONF_MANUFACTURER: TEST_MANUFACTURER,
            CONF_SERIAL_NUMBER: TEST_SERIALNUMBER,
            CONF_UPDATE_AUDYSSEY: TEST_UPDATE_AUDYSSEY,
        },
        title=TEST_NAME,
    )
    config_entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    result = await menuai.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SHOW_ALL_SOURCES: True,
            CONF_ZONE2: True,
            CONF_ZONE3: True,
            CONF_USE_TELNET: False,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options == {
        CONF_SHOW_ALL_SOURCES: True,
        CONF_ZONE2: True,
        CONF_ZONE3: True,
        CONF_UPDATE_AUDYSSEY: False,
        CONF_USE_TELNET: False,
    }


async def test_config_flow_manual_host_no_serial_double_config(
    menuai: menuai,
) -> None:
    """Failed flow manually initialized by the user twice.

    Host specified and an error getting the serial number.
    """
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    with patch(
        "menuai.components.denonavr.receiver.DenonAVR.serial_number",
        None,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: TEST_HOST},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_NAME
    assert result["data"] == {
        CONF_HOST: TEST_HOST,
        CONF_MODEL: TEST_MODEL,
        CONF_TYPE: TEST_RECEIVER_TYPE,
        CONF_MANUFACTURER: TEST_MANUFACTURER,
        CONF_SERIAL_NUMBER: None,
    }

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    with patch(
        "menuai.components.denonavr.receiver.DenonAVR.serial_number",
        None,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: TEST_HOST},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
