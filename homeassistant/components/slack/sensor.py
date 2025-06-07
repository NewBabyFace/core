"""Slack platform for sensor component."""

from __future__ import annotations

from slack_sdk.web.async_client import AsyncWebClient

from menuai.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback
from menuai.util import dt as dt_util

from .const import ATTR_SNOOZE, DOMAIN, SLACK_DATA
from .entity import SlackEntity


async def async_setup_entry(
    menuai: menuai,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Slack select."""
    async_add_entities(
        [
            SlackSensorEntity(
                menuai.data[DOMAIN][entry.entry_id][SLACK_DATA],
                SensorEntityDescription(
                    key="do_not_disturb_until",
                    translation_key="do_not_disturb_until",
                    device_class=SensorDeviceClass.TIMESTAMP,
                ),
                entry,
            )
        ],
        True,
    )


class SlackSensorEntity(SlackEntity, SensorEntity):
    """Representation of a Slack sensor."""

    _client: AsyncWebClient

    async def async_update(self) -> None:
        """Get the latest status."""
        if _time := (await self._client.dnd_info()).get(ATTR_SNOOZE):
            self._attr_native_value = dt_util.utc_from_timestamp(_time)
        else:
            self._attr_native_value = None
