"""Collection of helper methods.

All containing methods are legacy helpers that should not be used by new
components. Instead call the service directly.
"""

from menuai.components.scene import DOMAIN
from menuai.const import ATTR_ENTITY_ID, ENTITY_MATCH_ALL, SERVICE_TURN_ON
from menuai.core import menuai
from menuai.loader import bind_menuai


@bind_menuai
def activate(menuai: menuai, entity_id: str = ENTITY_MATCH_ALL) -> None:
    """Activate a scene."""
    data = {}

    if entity_id:
        data[ATTR_ENTITY_ID] = entity_id

    menuai.services.call(DOMAIN, SERVICE_TURN_ON, data)
