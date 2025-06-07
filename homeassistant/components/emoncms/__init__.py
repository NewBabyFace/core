"""The emoncms component."""

from pyemoncms import EmoncmsClient

from menuai.const import CONF_API_KEY, CONF_URL, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.issue_registry import IssueSeverity, async_create_issue

from .const import DOMAIN, EMONCMS_UUID_DOC_URL, LOGGER
from .coordinator import EmonCMSConfigEntry, EmoncmsCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


def _migrate_unique_id(
    menuai: menuai, entry: EmonCMSConfigEntry, emoncms_unique_id: str
) -> None:
    """Migrate to emoncms unique id if needed."""
    ent_reg = er.async_get(menuai)
    entry_entities = ent_reg.entities.get_entries_for_config_entry_id(entry.entry_id)
    for entity in entry_entities:
        if entity.unique_id.split("-")[0] == entry.entry_id:
            feed_id = entity.unique_id.split("-")[-1]
            LOGGER.debug("moving feed %s to hardware uuid", feed_id)
            ent_reg.async_update_entity(
                entity.entity_id, new_unique_id=f"{emoncms_unique_id}-{feed_id}"
            )
    menuai.config_entries.async_update_entry(
        entry,
        unique_id=emoncms_unique_id,
    )


async def _check_unique_id_migration(
    menuai: menuai, entry: EmonCMSConfigEntry, emoncms_client: EmoncmsClient
) -> None:
    """Check if we can migrate to the emoncms uuid."""
    emoncms_unique_id = await emoncms_client.async_get_uuid()
    if emoncms_unique_id:
        if entry.unique_id != emoncms_unique_id:
            _migrate_unique_id(menuai, entry, emoncms_unique_id)
    else:
        async_create_issue(
            menuai,
            DOMAIN,
            "migrate database",
            is_fixable=False,
            issue_domain=DOMAIN,
            severity=IssueSeverity.WARNING,
            translation_key="migrate_database",
            translation_placeholders={
                "url": entry.data[CONF_URL],
                "doc_url": EMONCMS_UUID_DOC_URL,
            },
        )


async def async_setup_entry(menuai: menuai, entry: EmonCMSConfigEntry) -> bool:
    """Load a config entry."""
    emoncms_client = EmoncmsClient(
        entry.data[CONF_URL],
        entry.data[CONF_API_KEY],
        session=async_get_clientsession(menuai),
    )
    await _check_unique_id_migration(menuai, entry, emoncms_client)
    coordinator = EmoncmsCoordinator(menuai, entry, emoncms_client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    entry.async_on_unload(entry.add_update_listener(update_listener))
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def update_listener(menuai: menuai, entry: EmonCMSConfigEntry):
    """Handle options update."""
    await menuai.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(menuai: menuai, entry: EmonCMSConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
