"""The tests for lutron caseta logbook."""

from menuai.components.lutron_caseta.const import (
    ATTR_ACTION,
    ATTR_AREA_NAME,
    ATTR_BUTTON_NUMBER,
    ATTR_DEVICE_NAME,
    ATTR_LEAP_BUTTON_NUMBER,
    ATTR_SERIAL,
    ATTR_TYPE,
    CONF_CA_CERTS,
    CONF_CERTFILE,
    CONF_KEYFILE,
    DOMAIN,
    LUTRON_CASETA_BUTTON_EVENT,
)
from menuai.components.lutron_caseta.models import LutronCasetaData
from menuai.const import ATTR_DEVICE_ID, CONF_HOST
from menuai.core import menuai
from menuai.helpers import device_registry as dr
from menuai.setup import async_setup_component

from . import MockBridge, async_setup_integration

from tests.common import MockConfigEntry
from tests.components.logbook.common import MockRow, mock_humanify


async def test_humanify_lutron_caseta_button_event(menuai: menuai) -> None:
    """Test humanifying lutron_caseta_button_events."""
    menuai.config.components.add("recorder")
    assert await async_setup_component(menuai, "logbook", {})
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "1.1.1.1",
            CONF_KEYFILE: "",
            CONF_CERTFILE: "",
            CONF_CA_CERTS: "",
        },
        unique_id="abc",
    )
    config_entry.add_to_menuai(menuai)
    await async_setup_integration(menuai, MockBridge, config_entry.entry_id)

    await menuai.async_block_till_done()

    # Fetching the config entry runtime_data is a legacy pattern
    # and should not be copied for new integrations
    data: LutronCasetaData = menuai.config_entries.async_get_entry(
        config_entry.entry_id
    ).runtime_data
    keypads = data.keypad_data.keypads
    keypad = keypads["9"]
    dr_device_id = keypad["dr_device_id"]

    (event1,) = mock_humanify(
        menuai,
        [
            MockRow(
                LUTRON_CASETA_BUTTON_EVENT,
                {
                    ATTR_SERIAL: "68551522",
                    ATTR_DEVICE_ID: dr_device_id,
                    ATTR_TYPE: "Pico3ButtonRaiseLower",
                    ATTR_LEAP_BUTTON_NUMBER: 1,
                    ATTR_BUTTON_NUMBER: 1,
                    ATTR_DEVICE_NAME: "Pico",
                    ATTR_AREA_NAME: "Dining Room",
                    ATTR_ACTION: "press",
                },
            ),
        ],
    )

    assert event1["name"] == "Dining Room Pico"
    assert event1["domain"] == DOMAIN
    assert event1["message"] == "press stop"


async def test_humanify_lutron_caseta_button_event_integration_not_loaded(
    menuai: menuai, device_registry: dr.DeviceRegistry
) -> None:
    """Test humanifying lutron_caseta_button_events when the integration fails to load."""
    menuai.config.components.add("recorder")
    assert await async_setup_component(menuai, "logbook", {})
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "1.1.1.1",
            CONF_KEYFILE: "",
            CONF_CERTFILE: "",
            CONF_CA_CERTS: "",
        },
        unique_id="abc",
    )
    config_entry.add_to_menuai(menuai)

    await async_setup_integration(menuai, MockBridge, config_entry.entry_id)

    await menuai.config_entries.async_unload(config_entry.entry_id)
    await menuai.async_block_till_done()

    for device in device_registry.devices.values():
        if device.config_entries == {config_entry.entry_id}:
            dr_device_id = device.id
            break

    assert dr_device_id is not None
    (event1,) = mock_humanify(
        menuai,
        [
            MockRow(
                LUTRON_CASETA_BUTTON_EVENT,
                {
                    ATTR_SERIAL: "68551522",
                    ATTR_DEVICE_ID: dr_device_id,
                    ATTR_TYPE: "Pico3ButtonRaiseLower",
                    ATTR_LEAP_BUTTON_NUMBER: 1,
                    ATTR_BUTTON_NUMBER: 1,
                    ATTR_DEVICE_NAME: "Pico",
                    ATTR_AREA_NAME: "Dining Room",
                    ATTR_ACTION: "press",
                },
            ),
        ],
    )

    assert event1["name"] == "Dining Room Pico"
    assert event1["domain"] == DOMAIN
    assert event1["message"] == "press stop"


async def test_humanify_lutron_caseta_button_event_ra3(
    menuai: menuai, device_registry: dr.DeviceRegistry
) -> None:
    """Test humanifying lutron_caseta_button_events from an RA3 hub."""
    menuai.config.components.add("recorder")
    assert await async_setup_component(menuai, "logbook", {})
    await async_setup_integration(menuai, MockBridge)

    keypad = device_registry.async_get_device(
        identifiers={(DOMAIN, 66286451)}, connections=set()
    )
    assert keypad

    (event1,) = mock_humanify(
        menuai,
        [
            MockRow(
                LUTRON_CASETA_BUTTON_EVENT,
                {
                    ATTR_SERIAL: "66286451",
                    ATTR_DEVICE_ID: keypad.id,
                    ATTR_TYPE: keypad.model,
                    ATTR_LEAP_BUTTON_NUMBER: 3,
                    ATTR_BUTTON_NUMBER: 3,
                    ATTR_DEVICE_NAME: "Keypad",
                    ATTR_AREA_NAME: "Breakfast",
                    ATTR_ACTION: "press",
                },
            ),
        ],
    )

    assert event1["name"] == "Breakfast Keypad"
    assert event1["domain"] == DOMAIN
    assert event1["message"] == "press Kitchen Pendants"


async def test_humanify_lutron_caseta_button_unknown_type(
    menuai: menuai, device_registry: dr.DeviceRegistry
) -> None:
    """Test humanifying lutron_caseta_button_events with an unknown type."""
    menuai.config.components.add("recorder")
    assert await async_setup_component(menuai, "logbook", {})
    await async_setup_integration(menuai, MockBridge)

    keypad = device_registry.async_get_device(
        identifiers={(DOMAIN, 66286451)}, connections=set()
    )
    assert keypad

    (event1,) = mock_humanify(
        menuai,
        [
            MockRow(
                LUTRON_CASETA_BUTTON_EVENT,
                {
                    ATTR_SERIAL: "66286451",
                    ATTR_DEVICE_ID: "removed",
                    ATTR_TYPE: keypad.model,
                    ATTR_LEAP_BUTTON_NUMBER: 3,
                    ATTR_BUTTON_NUMBER: 3,
                    ATTR_DEVICE_NAME: "Keypad",
                    ATTR_AREA_NAME: "Breakfast",
                    ATTR_ACTION: "press",
                },
            ),
        ],
    )

    assert event1["name"] == "Breakfast Keypad"
    assert event1["domain"] == DOMAIN
    assert event1["message"] == "press Error retrieving button description"
