"""Test the AlarmDecoder config flow."""

from unittest.mock import patch

from alarmdecoder.util import NoDeviceError
import pytest

from menuai import config_entries
from menuai.components.alarmdecoder import config_flow
from menuai.components.alarmdecoder.const import (
    CONF_ALT_NIGHT_MODE,
    CONF_AUTO_BYPASS,
    CONF_CODE_ARM_REQUIRED,
    CONF_DEVICE_BAUD,
    CONF_DEVICE_PATH,
    CONF_RELAY_ADDR,
    CONF_RELAY_CHAN,
    CONF_ZONE_LOOP,
    CONF_ZONE_NAME,
    CONF_ZONE_NUMBER,
    CONF_ZONE_RFID,
    CONF_ZONE_TYPE,
    DEFAULT_ARM_OPTIONS,
    DEFAULT_ZONE_OPTIONS,
    DOMAIN,
    OPTIONS_ARM,
    OPTIONS_ZONES,
    PROTOCOL_SERIAL,
    PROTOCOL_SOCKET,
)
from menuai.components.binary_sensor import BinarySensorDeviceClass
from menuai.const import CONF_HOST, CONF_PORT, CONF_PROTOCOL
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


@pytest.mark.parametrize(
    ("protocol", "connection", "title"),
    [
        (
            PROTOCOL_SOCKET,
            {
                CONF_HOST: "alarmdecoder123",
                CONF_PORT: 10001,
            },
            "alarmdecoder123:10001",
        ),
        (
            PROTOCOL_SERIAL,
            {
                CONF_DEVICE_PATH: "/dev/ttyUSB123",
                CONF_DEVICE_BAUD: 115000,
            },
            "/dev/ttyUSB123",
        ),
    ],
)
async def test_setups(menuai: menuai, protocol, connection, title) -> None:
    """Test flow for setting up the available AlarmDecoder protocols."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_PROTOCOL: protocol},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "protocol"

    with (
        patch("menuai.components.alarmdecoder.config_flow.AdExt.open"),
        patch("menuai.components.alarmdecoder.config_flow.AdExt.close"),
        patch(
            "menuai.components.alarmdecoder.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], connection
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == title
        assert result["data"] == {
            **connection,
            CONF_PROTOCOL: protocol,
        }
        await menuai.async_block_till_done()

    assert len(mock_setup_entry.mock_calls) == 1


async def test_setup_connection_error(menuai: menuai) -> None:
    """Test flow for setup with a connection error."""

    port = 1001
    host = "alarmdecoder"
    protocol = PROTOCOL_SOCKET
    connection_settings = {CONF_HOST: host, CONF_PORT: port}

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_PROTOCOL: protocol},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "protocol"

    with (
        patch(
            "menuai.components.alarmdecoder.config_flow.AdExt.open",
            side_effect=NoDeviceError,
        ),
        patch("menuai.components.alarmdecoder.config_flow.AdExt.close"),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], connection_settings
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}

    with (
        patch(
            "menuai.components.alarmdecoder.config_flow.AdExt.open",
            side_effect=Exception,
        ),
        patch("menuai.components.alarmdecoder.config_flow.AdExt.close"),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], connection_settings
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "unknown"}


async def test_options_arm_flow(menuai: menuai) -> None:
    """Test arm options flow."""
    user_input = {
        CONF_ALT_NIGHT_MODE: True,
        CONF_AUTO_BYPASS: True,
        CONF_CODE_ARM_REQUIRED: True,
    }
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    result = await menuai.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"edit_selection": "Arming Settings"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "arm_settings"

    with patch(
        "menuai.components.alarmdecoder.async_setup_entry", return_value=True
    ):
        result = await menuai.config_entries.options.async_configure(
            result["flow_id"],
            user_input=user_input,
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {
        OPTIONS_ARM: user_input,
        OPTIONS_ZONES: DEFAULT_ZONE_OPTIONS,
    }


async def test_options_zone_flow(menuai: menuai) -> None:
    """Test options flow for adding/deleting zones."""
    zone_number = "2"
    zone_settings = {
        CONF_ZONE_NAME: "Front Entry",
        CONF_ZONE_TYPE: BinarySensorDeviceClass.WINDOW,
    }
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    result = await menuai.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"edit_selection": "Zones"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "zone_select"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_ZONE_NUMBER: zone_number},
    )

    with patch(
        "menuai.components.alarmdecoder.async_setup_entry", return_value=True
    ):
        result = await menuai.config_entries.options.async_configure(
            result["flow_id"],
            user_input=zone_settings,
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {
        OPTIONS_ARM: DEFAULT_ARM_OPTIONS,
        OPTIONS_ZONES: {zone_number: zone_settings},
    }

    # Make sure zone can be removed...
    result = await menuai.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"edit_selection": "Zones"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "zone_select"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_ZONE_NUMBER: zone_number},
    )

    with patch(
        "menuai.components.alarmdecoder.async_setup_entry", return_value=True
    ):
        result = await menuai.config_entries.options.async_configure(
            result["flow_id"],
            user_input={},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {
        OPTIONS_ARM: DEFAULT_ARM_OPTIONS,
        OPTIONS_ZONES: {},
    }


async def test_options_zone_flow_validation(menuai: menuai) -> None:
    """Test input validation for zone options flow."""
    zone_number = "2"
    zone_settings = {
        CONF_ZONE_NAME: "Front Entry",
        CONF_ZONE_TYPE: BinarySensorDeviceClass.WINDOW,
    }
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    result = await menuai.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"edit_selection": "Zones"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "zone_select"

    # Zone Number must be int
    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_ZONE_NUMBER: "asd"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "zone_select"
    assert result["errors"] == {CONF_ZONE_NUMBER: "int"}

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_ZONE_NUMBER: zone_number},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "zone_details"

    # CONF_RELAY_ADDR & CONF_RELAY_CHAN are inclusive
    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={**zone_settings, CONF_RELAY_ADDR: "1"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "zone_details"
    assert result["errors"] == {"base": "relay_inclusive"}

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={**zone_settings, CONF_RELAY_CHAN: "1"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "zone_details"
    assert result["errors"] == {"base": "relay_inclusive"}

    # CONF_RELAY_ADDR, CONF_RELAY_CHAN must be int
    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={**zone_settings, CONF_RELAY_ADDR: "abc", CONF_RELAY_CHAN: "abc"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "zone_details"
    assert result["errors"] == {
        CONF_RELAY_ADDR: "int",
        CONF_RELAY_CHAN: "int",
    }

    # CONF_ZONE_LOOP depends on CONF_ZONE_RFID
    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={**zone_settings, CONF_ZONE_LOOP: "1"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "zone_details"
    assert result["errors"] == {CONF_ZONE_LOOP: "loop_rfid"}

    # CONF_ZONE_LOOP must be int
    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={**zone_settings, CONF_ZONE_RFID: "rfid123", CONF_ZONE_LOOP: "ab"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "zone_details"
    assert result["errors"] == {CONF_ZONE_LOOP: "int"}

    # CONF_ZONE_LOOP must be between [1,4]
    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={**zone_settings, CONF_ZONE_RFID: "rfid123", CONF_ZONE_LOOP: "5"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "zone_details"
    assert result["errors"] == {CONF_ZONE_LOOP: "loop_range"}

    # All valid settings
    with patch(
        "menuai.components.alarmdecoder.async_setup_entry", return_value=True
    ):
        result = await menuai.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                **zone_settings,
                CONF_ZONE_RFID: "rfid123",
                CONF_ZONE_LOOP: "2",
                CONF_RELAY_ADDR: "12",
                CONF_RELAY_CHAN: "1",
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {
        OPTIONS_ARM: DEFAULT_ARM_OPTIONS,
        OPTIONS_ZONES: {
            zone_number: {
                **zone_settings,
                CONF_ZONE_RFID: "rfid123",
                CONF_ZONE_LOOP: 2,
                CONF_RELAY_ADDR: 12,
                CONF_RELAY_CHAN: 1,
            }
        },
    }


@pytest.mark.parametrize(
    ("protocol", "connection"),
    [
        (
            PROTOCOL_SOCKET,
            {
                CONF_HOST: "alarmdecoder123",
                CONF_PORT: 10001,
            },
        ),
        (
            PROTOCOL_SERIAL,
            {
                CONF_DEVICE_PATH: "/dev/ttyUSB123",
                CONF_DEVICE_BAUD: 115000,
            },
        ),
    ],
)
async def test_one_device_allowed(menuai: menuai, protocol, connection) -> None:
    """Test that only one AlarmDecoder device is allowed."""
    flow = config_flow.AlarmDecoderFlowHandler()
    flow.menuai = menuai

    MockConfigEntry(
        domain=DOMAIN,
        data=connection,
    ).add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_PROTOCOL: protocol},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "protocol"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], connection
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
