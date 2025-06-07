"""A sensor for incoming calls using a USB modem that supports caller ID."""

from __future__ import annotations

from phone_modem import PhoneModem

from menuai.components.sensor import SensorEntity
from menuai.config_entries import ConfigEntry
from menuai.const import EVENT_menuai_STOP, STATE_IDLE
from menuai.core import Event, menuai, callback
from menuai.helpers.device_registry import DeviceInfo
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CID, DATA_KEY_API, DOMAIN


async def async_setup_entry(
    menuai: menuai,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Modem Caller ID sensor."""
    api = menuai.data[DOMAIN][entry.entry_id][DATA_KEY_API]
    async_add_entities(
        [
            ModemCalleridSensor(
                api,
                entry.entry_id,
            )
        ]
    )

    async def _async_on_menuai_stop(event: Event) -> None:
        """HA is shutting down, close modem port."""
        if menuai.data[DOMAIN][entry.entry_id][DATA_KEY_API]:
            await menuai.data[DOMAIN][entry.entry_id][DATA_KEY_API].close()

    entry.async_on_unload(
        menuai.bus.async_listen_once(EVENT_menuai_STOP, _async_on_menuai_stop)
    )


class ModemCalleridSensor(SensorEntity):
    """Implementation of USB modem caller ID sensor."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_name = None
    _attr_translation_key = "incoming_call"

    def __init__(self, api: PhoneModem, server_unique_id: str) -> None:
        """Initialize the sensor."""
        self.api = api
        self._attr_unique_id = server_unique_id
        self._attr_native_value = STATE_IDLE
        self._attr_extra_state_attributes = {
            CID.CID_TIME: 0,
            CID.CID_NUMBER: "",
            CID.CID_NAME: "",
        }
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, server_unique_id)})

    async def async_added_to_menuai(self) -> None:
        """Call when the modem sensor is added to MenuAI."""
        self.api.registercallback(self._async_incoming_call)
        await super().async_added_to_menuai()

    @callback
    def _async_incoming_call(self, new_state: str) -> None:
        """Handle new states."""
        self._attr_extra_state_attributes = {}
        if self.api.cid_name:
            self._attr_extra_state_attributes[CID.CID_NAME] = self.api.cid_name
        if self.api.cid_number:
            self._attr_extra_state_attributes[CID.CID_NUMBER] = self.api.cid_number
        if self.api.cid_time:
            self._attr_extra_state_attributes[CID.CID_TIME] = self.api.cid_time
        self._attr_native_value = self.api.state
        self.async_write_ha_state()
