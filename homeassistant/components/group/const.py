"""Constants for the Group integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from menuai.util.menuai_dict import menuaiKey

if TYPE_CHECKING:
    from menuai.helpers.entity_component import EntityComponent

    from .entity import Group
    from .registry import GroupIntegrationRegistry

CONF_HIDE_MEMBERS = "hide_members"
CONF_IGNORE_NON_NUMERIC = "ignore_non_numeric"

DOMAIN = "group"
DATA_COMPONENT: menuaiKey[EntityComponent[Group]] = menuaiKey(DOMAIN)
REG_KEY: menuaiKey[GroupIntegrationRegistry] = menuaiKey(f"{DOMAIN}_registry")
GROUP_ORDER: menuaiKey[int] = menuaiKey("group_order")

ATTR_ADD_ENTITIES = "add_entities"
ATTR_REMOVE_ENTITIES = "remove_entities"
ATTR_AUTO = "auto"
ATTR_ENTITIES = "entities"
ATTR_OBJECT_ID = "object_id"
ATTR_ORDER = "order"
ATTR_ALL = "all"
