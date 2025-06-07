"""Support for Wireless Sensor Tags."""

import logging

from wirelesstagpy.sensortag import SensorTag

from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def async_migrate_unique_id(
    menuai: menuai, tag: SensorTag, domain: str, key: str
) -> None:
    """Migrate old unique id to new one with use of tag's uuid."""
    registry = er.async_get(menuai)
    new_unique_id = f"{tag.uuid}_{key}"

    if registry.async_get_entity_id(domain, DOMAIN, new_unique_id):
        return

    old_unique_id = f"{tag.tag_id}_{key}"
    if entity_id := registry.async_get_entity_id(domain, DOMAIN, old_unique_id):
        _LOGGER.debug("Updating unique id for %s %s", key, entity_id)
        registry.async_update_entity(entity_id, new_unique_id=new_unique_id)
