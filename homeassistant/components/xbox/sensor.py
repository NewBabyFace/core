"""Xbox friends binary sensors."""

from __future__ import annotations

from functools import partial

from menuai.components.sensor import SensorEntity
from menuai.config_entries import ConfigEntry
from menuai.core import menuai, callback
from menuai.helpers import entity_registry as er
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import XboxUpdateCoordinator
from .entity import XboxBaseEntity

SENSOR_ATTRIBUTES = ["status", "gamer_score", "account_tier", "gold_tenure"]


async def async_setup_entry(
    menuai: menuai,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Xbox Live friends."""
    coordinator: XboxUpdateCoordinator = menuai.data[DOMAIN][config_entry.entry_id][
        "coordinator"
    ]

    update_friends = partial(async_update_friends, coordinator, {}, async_add_entities)

    unsub = coordinator.async_add_listener(update_friends)
    menuai.data[DOMAIN][config_entry.entry_id]["sensor_unsub"] = unsub
    update_friends()


class XboxSensorEntity(XboxBaseEntity, SensorEntity):
    """Representation of a Xbox presence state."""

    @property
    def native_value(self):
        """Return the state of the requested attribute."""
        if not self.coordinator.last_update_success:
            return None

        return getattr(self.data, self.attribute, None)


@callback
def async_update_friends(
    coordinator: XboxUpdateCoordinator,
    current: dict[str, list[XboxSensorEntity]],
    async_add_entities,
) -> None:
    """Update friends."""
    new_ids = set(coordinator.data.presence)
    current_ids = set(current)

    # Process new favorites, add them to MenuAI
    new_entities: list[XboxSensorEntity] = []
    for xuid in new_ids - current_ids:
        current[xuid] = [
            XboxSensorEntity(coordinator, xuid, attribute)
            for attribute in SENSOR_ATTRIBUTES
        ]
        new_entities = new_entities + current[xuid]

    async_add_entities(new_entities)

    # Process deleted favorites, remove them from MenuAI
    for xuid in current_ids - new_ids:
        coordinator.menuai.async_create_task(
            async_remove_entities(xuid, coordinator, current)
        )


async def async_remove_entities(
    xuid: str,
    coordinator: XboxUpdateCoordinator,
    current: dict[str, list[XboxSensorEntity]],
) -> None:
    """Remove friend sensors from MenuAI."""
    registry = er.async_get(coordinator.menuai)
    entities = current[xuid]
    for entity in entities:
        if entity.entity_id in registry.entities:
            registry.async_remove(entity.entity_id)
    del current[xuid]
