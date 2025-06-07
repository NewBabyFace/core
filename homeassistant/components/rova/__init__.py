"""The rova component."""

from __future__ import annotations

from requests.exceptions import ConnectTimeout, HTTPError
from rova.rova import Rova

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryError, ConfigEntryNotReady
from menuai.helpers.issue_registry import IssueSeverity, async_create_issue

from .const import CONF_HOUSE_NUMBER, CONF_HOUSE_NUMBER_SUFFIX, CONF_ZIP_CODE, DOMAIN
from .coordinator import RovaCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up ROVA from a config entry."""

    api = Rova(
        entry.data[CONF_ZIP_CODE],
        entry.data[CONF_HOUSE_NUMBER],
        entry.data[CONF_HOUSE_NUMBER_SUFFIX],
    )

    try:
        rova_area = await menuai.async_add_executor_job(api.is_rova_area)
    except (ConnectTimeout, HTTPError) as ex:
        raise ConfigEntryNotReady from ex

    if not rova_area:
        async_create_issue(
            menuai,
            DOMAIN,
            f"no_rova_area_{entry.data[CONF_ZIP_CODE]}",
            is_fixable=False,
            issue_domain=DOMAIN,
            severity=IssueSeverity.ERROR,
            translation_key="no_rova_area",
            translation_placeholders={
                CONF_ZIP_CODE: entry.data[CONF_ZIP_CODE],
            },
        )
        raise ConfigEntryError("Rova does not collect garbage in this area")

    coordinator = RovaCoordinator(menuai, entry, api)

    await coordinator.async_config_entry_first_refresh()

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload ROVA config entry."""

    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
