"""The jewish_calendar component."""

from __future__ import annotations

from functools import partial
import logging

from hdate import Location

from menuai.const import (
    CONF_ELEVATION,
    CONF_LANGUAGE,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_TIME_ZONE,
    Platform,
)
from menuai.core import menuai, callback
from menuai.helpers import config_validation as cv, entity_registry as er
from menuai.helpers.typing import ConfigType

from .const import (
    CONF_CANDLE_LIGHT_MINUTES,
    CONF_DIASPORA,
    CONF_HAVDALAH_OFFSET_MINUTES,
    DEFAULT_CANDLE_LIGHT,
    DEFAULT_DIASPORA,
    DEFAULT_HAVDALAH_OFFSET_MINUTES,
    DEFAULT_LANGUAGE,
    DOMAIN,
)
from .entity import JewishCalendarConfigEntry, JewishCalendarData
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the Jewish Calendar service."""
    async_setup_services(menuai)

    return True


async def async_setup_entry(
    menuai: menuai, config_entry: JewishCalendarConfigEntry
) -> bool:
    """Set up a configuration entry for Jewish calendar."""
    language = config_entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)
    diaspora = config_entry.data.get(CONF_DIASPORA, DEFAULT_DIASPORA)
    candle_lighting_offset = config_entry.options.get(
        CONF_CANDLE_LIGHT_MINUTES, DEFAULT_CANDLE_LIGHT
    )
    havdalah_offset = config_entry.options.get(
        CONF_HAVDALAH_OFFSET_MINUTES, DEFAULT_HAVDALAH_OFFSET_MINUTES
    )

    location = await menuai.async_add_executor_job(
        partial(
            Location,
            name=menuai.config.location_name,
            diaspora=diaspora,
            latitude=config_entry.data.get(CONF_LATITUDE, menuai.config.latitude),
            longitude=config_entry.data.get(CONF_LONGITUDE, menuai.config.longitude),
            altitude=config_entry.data.get(CONF_ELEVATION, menuai.config.elevation),
            timezone=config_entry.data.get(CONF_TIME_ZONE, menuai.config.time_zone),
        )
    )

    config_entry.runtime_data = JewishCalendarData(
        language,
        diaspora,
        location,
        candle_lighting_offset,
        havdalah_offset,
    )

    await menuai.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    async def update_listener(
        menuai: menuai, config_entry: JewishCalendarConfigEntry
    ) -> None:
        # Trigger update of states for all platforms
        await menuai.config_entries.async_reload(config_entry.entry_id)

    config_entry.async_on_unload(config_entry.add_update_listener(update_listener))
    return True


async def async_unload_entry(
    menuai: menuai, config_entry: JewishCalendarConfigEntry
) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(config_entry, PLATFORMS)


async def async_migrate_entry(
    menuai: menuai, config_entry: JewishCalendarConfigEntry
) -> bool:
    """Migrate old entry."""

    _LOGGER.debug("Migrating from version %s", config_entry.version)

    @callback
    def update_unique_id(
        entity_entry: er.RegistryEntry,
    ) -> dict[str, str] | None:
        """Update unique ID of entity entry."""
        key_translations = {
            "first_light": "alot_hashachar",
            "talit": "talit_and_tefillin",
            "sunrise": "netz_hachama",
            "gra_end_shma": "sof_zman_shema_gra",
            "mga_end_shma": "sof_zman_shema_mga",
            "gra_end_tfila": "sof_zman_tfilla_gra",
            "mga_end_tfila": "sof_zman_tfilla_mga",
            "midday": "chatzot_hayom",
            "big_mincha": "mincha_gedola",
            "small_mincha": "mincha_ketana",
            "plag_mincha": "plag_hamincha",
            "sunset": "shkia",
            "first_stars": "tset_hakohavim_tsom",
            "three_stars": "tset_hakohavim_shabbat",
        }
        old_keys = tuple(key_translations.keys())
        if entity_entry.unique_id.endswith(old_keys):
            old_key = entity_entry.unique_id.split("-")[1]
            new_unique_id = f"{config_entry.entry_id}-{key_translations[old_key]}"
            return {"new_unique_id": new_unique_id}
        return None

    if config_entry.version > 2:
        # This means the user has downgraded from a future version
        return False

    if config_entry.version == 1:
        await er.async_migrate_entries(menuai, config_entry.entry_id, update_unique_id)
        menuai.config_entries.async_update_entry(config_entry, version=2)

    if config_entry.version == 2:
        new_data = {**config_entry.data}
        new_data[CONF_LANGUAGE] = config_entry.data[CONF_LANGUAGE][:2]
        menuai.config_entries.async_update_entry(config_entry, data=new_data, version=3)

    return True
