"""The template component."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
import logging
from typing import Any

from menuai import config as conf_util
from menuai.config_entries import ConfigEntry
from menuai.const import (
    CONF_DEVICE_ID,
    CONF_NAME,
    CONF_TRIGGERS,
    CONF_UNIQUE_ID,
    SERVICE_RELOAD,
)
from menuai.core import Event, menuai, ServiceCall
from menuai.exceptions import ConfigEntryError, menuaiError
from menuai.helpers import discovery
from menuai.helpers.device import (
    async_remove_stale_devices_links_keep_current_device,
)
from menuai.helpers.reload import async_reload_integration_platforms
from menuai.helpers.service import async_register_admin_service
from menuai.helpers.typing import ConfigType
from menuai.loader import async_get_integration
from menuai.util.menuai_dict import menuaiKey

from .const import CONF_MAX, CONF_MIN, CONF_STEP, DOMAIN, PLATFORMS
from .coordinator import TriggerUpdateCoordinator
from .helpers import async_get_blueprints

_LOGGER = logging.getLogger(__name__)
DATA_COORDINATORS: menuaiKey[list[TriggerUpdateCoordinator]] = menuaiKey(DOMAIN)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the template integration."""

    # Register template as valid domain for Blueprint
    blueprints = async_get_blueprints(menuai)

    # Add some default blueprints to blueprints/template, does nothing
    # if blueprints/template already exists but still has to create
    # an executor job to check if the folder exists so we run it in a
    # separate task to avoid waiting for it to finish setting up
    # since a tracked task will be waited at the end of startup
    menuai.async_create_task(blueprints.async_populate(), eager_start=True)

    if DOMAIN in config:
        await _process_config(menuai, config)

    async def _reload_config(call: Event | ServiceCall) -> None:
        """Reload top-level + platforms."""
        await async_get_blueprints(menuai).async_reset_cache()
        try:
            unprocessed_conf = await conf_util.async_menuai_config_yaml(menuai)
        except menuaiError as err:
            _LOGGER.error(err)
            return

        integration = await async_get_integration(menuai, DOMAIN)
        conf = await conf_util.async_process_component_and_handle_errors(
            menuai, unprocessed_conf, integration
        )

        if conf is None:
            return

        await async_reload_integration_platforms(menuai, DOMAIN, PLATFORMS)

        if DOMAIN in conf:
            await _process_config(menuai, conf)

        menuai.bus.async_fire(f"event_{DOMAIN}_reloaded", context=call.context)

    async_register_admin_service(menuai, DOMAIN, SERVICE_RELOAD, _reload_config)

    return True


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up a config entry."""

    async_remove_stale_devices_links_keep_current_device(
        menuai,
        entry.entry_id,
        entry.options.get(CONF_DEVICE_ID),
    )

    for key in (CONF_MAX, CONF_MIN, CONF_STEP):
        if key not in entry.options:
            continue
        if isinstance(entry.options[key], str):
            raise ConfigEntryError(
                f"The '{entry.options.get(CONF_NAME) or ''}' number template needs to "
                f"be reconfigured, {key} must be a number, got '{entry.options[key]}'"
            )

    await menuai.config_entries.async_forward_entry_setups(
        entry, (entry.options["template_type"],)
    )
    entry.async_on_unload(entry.add_update_listener(config_entry_update_listener))
    return True


async def config_entry_update_listener(menuai: menuai, entry: ConfigEntry) -> None:
    """Update listener, called when the config entry options are changed."""
    await menuai.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(
        entry, (entry.options["template_type"],)
    )


async def _process_config(menuai: menuai, menuai_config: ConfigType) -> None:
    """Process config."""
    coordinators = menuai.data.pop(DATA_COORDINATORS, None)

    # Remove old ones
    if coordinators:
        for coordinator in coordinators:
            coordinator.async_remove()

    async def init_coordinator(
        menuai: menuai, conf_section: dict[str, Any]
    ) -> TriggerUpdateCoordinator:
        coordinator = TriggerUpdateCoordinator(menuai, conf_section)
        await coordinator.async_setup(menuai_config)
        return coordinator

    coordinator_tasks: list[Coroutine[Any, Any, TriggerUpdateCoordinator]] = []

    for conf_section in menuai_config[DOMAIN]:
        if CONF_TRIGGERS in conf_section:
            coordinator_tasks.append(init_coordinator(menuai, conf_section))
            continue

        for platform_domain in PLATFORMS:
            if platform_domain in conf_section:
                menuai.async_create_task(
                    discovery.async_load_platform(
                        menuai,
                        platform_domain,
                        DOMAIN,
                        {
                            "unique_id": conf_section.get(CONF_UNIQUE_ID),
                            "entities": [
                                {
                                    **entity_conf,
                                    "raw_blueprint_inputs": conf_section.raw_blueprint_inputs,
                                    "raw_configs": conf_section.raw_config,
                                }
                                for entity_conf in conf_section[platform_domain]
                            ],
                        },
                        menuai_config,
                    ),
                    eager_start=True,
                )

    if coordinator_tasks:
        menuai.data[DATA_COORDINATORS] = await asyncio.gather(*coordinator_tasks)
