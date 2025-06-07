"""Collection of helper methods.

All containing methods are legacy helpers that should not be used by new
components. Instead call the service directly.
"""

from typing import Any

from menuai.components.vacuum import (
    ATTR_FAN_SPEED,
    ATTR_PARAMS,
    DOMAIN,
    SERVICE_CLEAN_SPOT,
    SERVICE_LOCATE,
    SERVICE_PAUSE,
    SERVICE_RETURN_TO_BASE,
    SERVICE_SEND_COMMAND,
    SERVICE_SET_FAN_SPEED,
    SERVICE_START,
    SERVICE_START_PAUSE,
    SERVICE_STOP,
)
from menuai.const import (
    ATTR_COMMAND,
    ATTR_ENTITY_ID,
    ENTITY_MATCH_ALL,
    SERVICE_TOGGLE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from menuai.core import menuai
from menuai.loader import bind_menuai


@bind_menuai
def turn_on(menuai: menuai, entity_id: str = ENTITY_MATCH_ALL) -> None:
    """Turn all or specified vacuum on."""
    menuai.add_job(async_turn_on, menuai, entity_id)


async def async_turn_on(menuai: menuai, entity_id: str = ENTITY_MATCH_ALL) -> None:
    """Turn all or specified vacuum on."""
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else None
    await menuai.services.async_call(DOMAIN, SERVICE_TURN_ON, data, blocking=True)


@bind_menuai
def turn_off(menuai: menuai, entity_id: str = ENTITY_MATCH_ALL) -> None:
    """Turn all or specified vacuum off."""
    menuai.add_job(async_turn_off, menuai, entity_id)


async def async_turn_off(
    menuai: menuai, entity_id: str = ENTITY_MATCH_ALL
) -> None:
    """Turn all or specified vacuum off."""
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else None
    await menuai.services.async_call(DOMAIN, SERVICE_TURN_OFF, data, blocking=True)


@bind_menuai
def toggle(menuai: menuai, entity_id: str = ENTITY_MATCH_ALL) -> None:
    """Toggle all or specified vacuum."""
    menuai.add_job(async_toggle, menuai, entity_id)


async def async_toggle(menuai: menuai, entity_id: str = ENTITY_MATCH_ALL) -> None:
    """Toggle all or specified vacuum."""
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else None
    await menuai.services.async_call(DOMAIN, SERVICE_TOGGLE, data, blocking=True)


@bind_menuai
def locate(menuai: menuai, entity_id: str = ENTITY_MATCH_ALL) -> None:
    """Locate all or specified vacuum."""
    menuai.add_job(async_locate, menuai, entity_id)


async def async_locate(menuai: menuai, entity_id: str = ENTITY_MATCH_ALL) -> None:
    """Locate all or specified vacuum."""
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else None
    await menuai.services.async_call(DOMAIN, SERVICE_LOCATE, data, blocking=True)


@bind_menuai
def clean_spot(menuai: menuai, entity_id: str = ENTITY_MATCH_ALL) -> None:
    """Tell all or specified vacuum to perform a spot clean-up."""
    menuai.add_job(async_clean_spot, menuai, entity_id)


async def async_clean_spot(
    menuai: menuai, entity_id: str = ENTITY_MATCH_ALL
) -> None:
    """Tell all or specified vacuum to perform a spot clean-up."""
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else None
    await menuai.services.async_call(DOMAIN, SERVICE_CLEAN_SPOT, data, blocking=True)


@bind_menuai
def return_to_base(menuai: menuai, entity_id: str = ENTITY_MATCH_ALL) -> None:
    """Tell all or specified vacuum to return to base."""
    menuai.add_job(async_return_to_base, menuai, entity_id)


async def async_return_to_base(
    menuai: menuai, entity_id: str = ENTITY_MATCH_ALL
) -> None:
    """Tell all or specified vacuum to return to base."""
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else None
    await menuai.services.async_call(DOMAIN, SERVICE_RETURN_TO_BASE, data, blocking=True)


@bind_menuai
def start_pause(menuai: menuai, entity_id: str = ENTITY_MATCH_ALL) -> None:
    """Tell all or specified vacuum to start or pause the current task."""
    menuai.add_job(async_start_pause, menuai, entity_id)


async def async_start_pause(
    menuai: menuai, entity_id: str = ENTITY_MATCH_ALL
) -> None:
    """Tell all or specified vacuum to start or pause the current task."""
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else None
    await menuai.services.async_call(DOMAIN, SERVICE_START_PAUSE, data, blocking=True)


@bind_menuai
def start(menuai: menuai, entity_id: str = ENTITY_MATCH_ALL) -> None:
    """Tell all or specified vacuum to start or resume the current task."""
    menuai.add_job(async_start, menuai, entity_id)


async def async_start(menuai: menuai, entity_id: str = ENTITY_MATCH_ALL) -> None:
    """Tell all or specified vacuum to start or resume the current task."""
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else None
    await menuai.services.async_call(DOMAIN, SERVICE_START, data, blocking=True)


@bind_menuai
def pause(menuai: menuai, entity_id: str = ENTITY_MATCH_ALL) -> None:
    """Tell all or the specified vacuum to pause the current task."""
    menuai.add_job(async_pause, menuai, entity_id)


async def async_pause(menuai: menuai, entity_id: str = ENTITY_MATCH_ALL) -> None:
    """Tell all or the specified vacuum to pause the current task."""
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else None
    await menuai.services.async_call(DOMAIN, SERVICE_PAUSE, data, blocking=True)


@bind_menuai
def stop(menuai: menuai, entity_id: str = ENTITY_MATCH_ALL) -> None:
    """Stop all or specified vacuum."""
    menuai.add_job(async_stop, menuai, entity_id)


async def async_stop(menuai: menuai, entity_id: str = ENTITY_MATCH_ALL) -> None:
    """Stop all or specified vacuum."""
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else None
    await menuai.services.async_call(DOMAIN, SERVICE_STOP, data, blocking=True)


@bind_menuai
def set_fan_speed(
    menuai: menuai, fan_speed: str, entity_id: str = ENTITY_MATCH_ALL
) -> None:
    """Set fan speed for all or specified vacuum."""
    menuai.add_job(async_set_fan_speed, menuai, fan_speed, entity_id)


async def async_set_fan_speed(
    menuai: menuai, fan_speed: str, entity_id: str = ENTITY_MATCH_ALL
) -> None:
    """Set fan speed for all or specified vacuum."""
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}
    data[ATTR_FAN_SPEED] = fan_speed
    await menuai.services.async_call(DOMAIN, SERVICE_SET_FAN_SPEED, data, blocking=True)


@bind_menuai
def send_command(
    menuai: menuai,
    command: str,
    params: dict[str, Any] | list[Any] | None = None,
    entity_id: str = ENTITY_MATCH_ALL,
) -> None:
    """Send command to all or specified vacuum."""
    menuai.add_job(async_send_command, menuai, command, params, entity_id)


async def async_send_command(
    menuai: menuai,
    command: str,
    params: dict[str, Any] | list[Any] | None = None,
    entity_id: str = ENTITY_MATCH_ALL,
) -> None:
    """Send command to all or specified vacuum."""
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}
    data[ATTR_COMMAND] = command
    if params is not None:
        data[ATTR_PARAMS] = params
    await menuai.services.async_call(DOMAIN, SERVICE_SEND_COMMAND, data, blocking=True)
