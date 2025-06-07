"""Allow users to set and activate scenes."""

from __future__ import annotations

import functools as ft
import importlib
import logging
from typing import Any, Final, final

import voluptuous as vol

from menuai.components.light import ATTR_TRANSITION
from menuai.config_entries import ConfigEntry
from menuai.const import CONF_PLATFORM, SERVICE_TURN_ON, STATE_UNAVAILABLE
from menuai.core import DOMAIN as menuai_DOMAIN, menuai
from menuai.helpers.entity_component import EntityComponent
from menuai.helpers.restore_state import RestoreEntity
from menuai.helpers.typing import ConfigType
from menuai.util import dt as dt_util
from menuai.util.menuai_dict import menuaiKey

DOMAIN: Final = "scene"
DATA_COMPONENT: menuaiKey[EntityComponent[Scene]] = menuaiKey(DOMAIN)
STATES: Final = "states"


def _menuai_domain_validator(config: dict[str, Any]) -> dict[str, Any]:
    """Validate platform in config for menuai domain."""
    if CONF_PLATFORM not in config:
        config = {CONF_PLATFORM: menuai_DOMAIN, STATES: config}

    return config


def _platform_validator(config: dict[str, Any]) -> dict[str, Any]:
    """Validate it is a valid  platform."""
    platform_name = config[CONF_PLATFORM]
    try:
        platform = importlib.import_module(
            f"menuai.components.{platform_name}.scene"
        )
    except ImportError:
        raise vol.Invalid("Invalid platform specified") from None

    if not hasattr(platform, "PLATFORM_SCHEMA"):
        return config

    return platform.PLATFORM_SCHEMA(config)  # type: ignore[no-any-return]


PLATFORM_SCHEMA = vol.Schema(
    vol.All(
        _menuai_domain_validator,
        vol.Schema({vol.Required(CONF_PLATFORM): str}, extra=vol.ALLOW_EXTRA),
        _platform_validator,
    ),
    extra=vol.ALLOW_EXTRA,
)

# mypy: disallow-any-generics


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the scenes."""
    component = menuai.data[DATA_COMPONENT] = EntityComponent[Scene](
        logging.getLogger(__name__), DOMAIN, menuai
    )

    await component.async_setup(config)
    # Ensure MenuAI platform always loaded.
    menuai.async_create_task(
        component.async_setup_platform(
            menuai_DOMAIN, {"platform": menuai_DOMAIN, STATES: []}
        ),
        eager_start=True,
    )
    component.async_register_entity_service(
        SERVICE_TURN_ON,
        {ATTR_TRANSITION: vol.All(vol.Coerce(float), vol.Clamp(min=0, max=6553))},
        "_async_activate",
    )

    return True


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    return await menuai.data[DATA_COMPONENT].async_setup_entry(entry)


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.data[DATA_COMPONENT].async_unload_entry(entry)


class Scene(RestoreEntity):
    """A scene is a group of entities and the states we want them to be."""

    _attr_should_poll = False
    __last_activated: str | None = None

    @property
    @final
    def state(self) -> str | None:
        """Return the state of the scene."""
        if self.__last_activated is None:
            return None
        return self.__last_activated

    @final
    async def _async_activate(self, **kwargs: Any) -> None:
        """Activate scene.

        Should not be overridden, handle setting last press timestamp.
        """
        self.__last_activated = dt_util.utcnow().isoformat()
        self.async_write_ha_state()
        await self.async_activate(**kwargs)

    async def async_internal_added_to_menuai(self) -> None:
        """Call when the scene is added to menuai."""
        await super().async_internal_added_to_menuai()
        state = await self.async_get_last_state()
        if (
            state is not None
            and state.state is not None
            and state.state != STATE_UNAVAILABLE
        ):
            self.__last_activated = state.state

    def activate(self, **kwargs: Any) -> None:
        """Activate scene. Try to get entities into requested state."""
        raise NotImplementedError

    async def async_activate(self, **kwargs: Any) -> None:
        """Activate scene. Try to get entities into requested state."""
        task = self.menuai.async_add_executor_job(ft.partial(self.activate, **kwargs))
        if task:
            await task
