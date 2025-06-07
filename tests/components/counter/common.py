"""Collection of helper methods.

All containing methods are legacy helpers that should not be used by new
components. Instead call the service directly.
"""

from menuai.components.counter import (
    DOMAIN,
    SERVICE_DECREMENT,
    SERVICE_INCREMENT,
    SERVICE_RESET,
)
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai, callback
from menuai.loader import bind_menuai


@callback
@bind_menuai
def async_increment(menuai: menuai, entity_id: str) -> None:
    """Increment a counter."""
    menuai.async_create_task(
        menuai.services.async_call(DOMAIN, SERVICE_INCREMENT, {ATTR_ENTITY_ID: entity_id})
    )


@callback
@bind_menuai
def async_decrement(menuai: menuai, entity_id: str) -> None:
    """Decrement a counter."""
    menuai.async_create_task(
        menuai.services.async_call(DOMAIN, SERVICE_DECREMENT, {ATTR_ENTITY_ID: entity_id})
    )


@callback
@bind_menuai
def async_reset(menuai: menuai, entity_id: str) -> None:
    """Reset a counter."""
    menuai.async_create_task(
        menuai.services.async_call(DOMAIN, SERVICE_RESET, {ATTR_ENTITY_ID: entity_id})
    )
