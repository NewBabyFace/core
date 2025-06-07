"""Entity representing a Blue Current charge point."""

from menuai.const import ATTR_NAME
from menuai.core import callback
from menuai.helpers.device_registry import DeviceInfo
from menuai.helpers.dispatcher import async_dispatcher_connect
from menuai.helpers.entity import Entity

from . import Connector
from .const import DOMAIN, MODEL_TYPE


class BlueCurrentEntity(Entity):
    """Define a base Blue Current entity."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    has_value = False

    def __init__(self, connector: Connector, signal: str) -> None:
        """Initialize the entity."""
        self.connector = connector
        self.signal = signal

    async def async_added_to_menuai(self) -> None:
        """Register callbacks."""

        @callback
        def update() -> None:
            """Update the state."""
            self.update_from_latest_data()
            self.async_write_ha_state()

        self.async_on_remove(async_dispatcher_connect(self.menuai, self.signal, update))

        self.update_from_latest_data()

    @property
    def available(self) -> bool:
        """Return entity availability."""
        return self.connector.connected and self.has_value

    @callback
    def update_from_latest_data(self) -> None:
        """Update the entity from the latest data."""


class ChargepointEntity(BlueCurrentEntity):
    """Define a base charge point entity."""

    def __init__(self, connector: Connector, evse_id: str) -> None:
        """Initialize the entity."""
        super().__init__(connector, f"{DOMAIN}_charge_point_update_{evse_id}")

        chargepoint_name = connector.charge_points[evse_id][ATTR_NAME]

        self.evse_id = evse_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, evse_id)},
            name=chargepoint_name if chargepoint_name != "" else evse_id,
            manufacturer="Blue Current",
            model=connector.charge_points[evse_id][MODEL_TYPE],
        )
