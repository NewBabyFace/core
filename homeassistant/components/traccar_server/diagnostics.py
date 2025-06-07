"""Diagnostics platform for Traccar Server."""

from __future__ import annotations

from typing import Any

from menuai.components.diagnostics import REDACTED, async_redact_data
from menuai.config_entries import ConfigEntry
from menuai.const import CONF_ADDRESS, CONF_LATITUDE, CONF_LONGITUDE
from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er

from .const import DOMAIN
from .coordinator import TraccarServerCoordinator

KEYS_TO_REDACT = {
    "area",  # This is the polygon area of a geofence
    CONF_ADDRESS,
    CONF_LATITUDE,
    CONF_LONGITUDE,
}


def _entity_state(
    menuai: menuai,
    entity: er.RegistryEntry,
    coordinator: TraccarServerCoordinator,
) -> dict[str, Any] | None:
    states_to_redact = {x["position"]["address"] for x in coordinator.data.values()}
    return (
        {
            "state": state.state if state.state not in states_to_redact else REDACTED,
            "attributes": state.attributes,
        }
        if (state := menuai.states.get(entity.entity_id))
        else None
    )


async def async_get_config_entry_diagnostics(
    menuai: menuai,
    config_entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: TraccarServerCoordinator = menuai.data[DOMAIN][config_entry.entry_id]
    entity_registry = er.async_get(menuai)

    entities = er.async_entries_for_config_entry(
        entity_registry,
        config_entry_id=config_entry.entry_id,
    )

    return async_redact_data(
        {
            "subscription_status": coordinator.client.subscription_status,
            "config_entry_options": dict(config_entry.options),
            "coordinator_data": coordinator.data,
            "entities": [
                {
                    "entity_id": entity.entity_id,
                    "disabled": entity.disabled,
                    "unit_of_measurement": entity.unit_of_measurement,
                    "state": _entity_state(menuai, entity, coordinator),
                }
                for entity in entities
            ],
        },
        KEYS_TO_REDACT,
    )


async def async_get_device_diagnostics(
    menuai: menuai,
    entry: ConfigEntry,
    device: dr.DeviceEntry,
) -> dict[str, Any]:
    """Return device diagnostics."""
    coordinator: TraccarServerCoordinator = menuai.data[DOMAIN][entry.entry_id]
    entity_registry = er.async_get(menuai)

    entities = er.async_entries_for_device(
        entity_registry,
        device_id=device.id,
        include_disabled_entities=True,
    )

    await menuai.config_entries.async_reload(entry.entry_id)
    return async_redact_data(
        {
            "subscription_status": coordinator.client.subscription_status,
            "config_entry_options": dict(entry.options),
            "coordinator_data": coordinator.data,
            "entities": [
                {
                    "entity_id": entity.entity_id,
                    "disabled": entity.disabled,
                    "unit_of_measurement": entity.unit_of_measurement,
                    "state": _entity_state(menuai, entity, coordinator),
                }
                for entity in entities
            ],
        },
        KEYS_TO_REDACT,
    )
