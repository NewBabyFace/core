"""Collection of helper methods.

All containing methods are legacy helpers that should not be used by new
components. Instead call the service directly.
"""

from menuai.components.image_processing import DOMAIN, SERVICE_SCAN
from menuai.const import ATTR_ENTITY_ID, ENTITY_MATCH_ALL
from menuai.core import menuai, callback
from menuai.loader import bind_menuai


@bind_menuai
def scan(menuai: menuai, entity_id: str = ENTITY_MATCH_ALL) -> None:
    """Force process of all cameras or given entity."""
    menuai.add_job(async_scan, menuai, entity_id)


@callback
@bind_menuai
def async_scan(menuai: menuai, entity_id: str = ENTITY_MATCH_ALL) -> None:
    """Force process of all cameras or given entity."""
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else None
    menuai.async_create_task(menuai.services.async_call(DOMAIN, SERVICE_SCAN, data))
