"""Collection of helper methods.

All containing methods are legacy helpers that should not be used by new
components. Instead call the service directly.
"""

from menuai.components.group import (
    ATTR_ADD_ENTITIES,
    ATTR_ENTITIES,
    ATTR_OBJECT_ID,
    DOMAIN,
    SERVICE_REMOVE,
    SERVICE_SET,
)
from menuai.const import ATTR_ICON, ATTR_NAME, SERVICE_RELOAD
from menuai.core import menuai, callback
from menuai.loader import bind_menuai


@bind_menuai
def reload(menuai: menuai) -> None:
    """Reload the automation from config."""
    menuai.add_job(async_reload, menuai)


@callback
@bind_menuai
def async_reload(menuai: menuai) -> None:
    """Reload the automation from config."""
    menuai.async_create_task(menuai.services.async_call(DOMAIN, SERVICE_RELOAD))


@bind_menuai
def set_group(
    menuai: menuai,
    object_id: str,
    name: str | None = None,
    entity_ids: list[str] | None = None,
    icon: str | None = None,
    add: list[str] | None = None,
) -> None:
    """Create/Update a group."""
    menuai.add_job(
        async_set_group,
        menuai,
        object_id,
        name,
        entity_ids,
        icon,
        add,
    )


@callback
@bind_menuai
def async_set_group(
    menuai: menuai,
    object_id: str,
    name: str | None = None,
    entity_ids: list[str] | None = None,
    icon: str | None = None,
    add: list[str] | None = None,
) -> None:
    """Create/Update a group."""
    data = {
        key: value
        for key, value in (
            (ATTR_OBJECT_ID, object_id),
            (ATTR_NAME, name),
            (ATTR_ENTITIES, entity_ids),
            (ATTR_ICON, icon),
            (ATTR_ADD_ENTITIES, add),
        )
        if value is not None
    }

    menuai.async_create_task(menuai.services.async_call(DOMAIN, SERVICE_SET, data))


@callback
@bind_menuai
def async_remove(menuai: menuai, object_id: str) -> None:
    """Remove a user group."""
    data = {ATTR_OBJECT_ID: object_id}
    menuai.async_create_task(menuai.services.async_call(DOMAIN, SERVICE_REMOVE, data))
