"""Integration providing core pieces of infrastructure."""

import asyncio
from collections.abc import Callable, Coroutine
import itertools as it
import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol

from menuai import config as conf_util, core_config
from menuai.auth.permissions.const import CAT_ENTITIES, POLICY_CONTROL
from menuai.components import persistent_notification
from menuai.const import (
    ATTR_ELEVATION,
    ATTR_ENTITY_ID,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    RESTART_EXIT_CODE,
    SERVICE_RELOAD,
    SERVICE_SAVE_PERSISTENT_STATES,
    SERVICE_TOGGLE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from menuai.core import (
    menuai,
    ServiceCall,
    ServiceResponse,
    callback,
    split_entity_id,
)
from menuai.exceptions import menuaiError, Unauthorized, UnknownUser
from menuai.helpers import (
    config_validation as cv,
    issue_registry as ir,
    recorder,
    restore_state,
)
from menuai.helpers.entity_component import async_update_entity
from menuai.helpers.importlib import async_import_module
from menuai.helpers.issue_registry import IssueSeverity
from menuai.helpers.service import (
    async_extract_config_entry_ids,
    async_extract_referenced_entity_ids,
    async_register_admin_service,
)
from menuai.helpers.signal import KEY_HA_STOP
from menuai.helpers.system_info import async_get_system_info
from menuai.helpers.template import async_load_custom_templates
from menuai.helpers.typing import ConfigType

# The scene integration will do a late import of scene
# so we want to make sure its loaded with the component
# so its already in memory when its imported so the import
# does not do blocking I/O in the event loop.
from . import scene as scene_pre_import  # noqa: F401
from .const import (
    DATA_EXPOSED_ENTITIES,
    DATA_STOP_HANDLER,
    DOMAIN,
    SERVICE_menuai_RESTART,
    SERVICE_menuai_STOP,
)
from .exposed_entities import ExposedEntities, async_should_expose  # noqa: F401

ATTR_ENTRY_ID = "entry_id"
ATTR_SAFE_MODE = "safe_mode"

_LOGGER = logging.getLogger(__name__)
SERVICE_RELOAD_CORE_CONFIG = "reload_core_config"
SERVICE_RELOAD_CONFIG_ENTRY = "reload_config_entry"
SERVICE_RELOAD_CUSTOM_TEMPLATES = "reload_custom_templates"
SERVICE_CHECK_CONFIG = "check_config"
SERVICE_UPDATE_ENTITY = "update_entity"
SERVICE_SET_LOCATION = "set_location"
SERVICE_RELOAD_ALL = "reload_all"
SCHEMA_UPDATE_ENTITY = vol.Schema({ATTR_ENTITY_ID: cv.entity_ids})
SCHEMA_RELOAD_CONFIG_ENTRY = vol.All(
    vol.Schema(
        {
            vol.Optional(ATTR_ENTRY_ID): str,
            **cv.ENTITY_SERVICE_FIELDS,
        },
    ),
    cv.has_at_least_one_key(ATTR_ENTRY_ID, *cv.ENTITY_SERVICE_FIELDS),
)
SCHEMA_RESTART = vol.Schema({vol.Optional(ATTR_SAFE_MODE, default=False): bool})

SHUTDOWN_SERVICES = (SERVICE_menuai_STOP, SERVICE_menuai_RESTART)

DEPRECATION_URL = (
    "https://www.home-assistant.io/blog/2025/05/22/"
    "deprecating-core-and-supervised-installation-methods-and-32-bit-systems/"
)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:  # noqa: C901
    """Set up general services related to MenuAI."""

    async def async_save_persistent_states(service: ServiceCall) -> None:
        """Handle calls to menuai.save_persistent_states."""
        await restore_state.RestoreStateData.async_save_persistent_states(menuai)

    async def async_handle_turn_service(service: ServiceCall) -> None:
        """Handle calls to menuai.turn_on/off."""
        referenced = async_extract_referenced_entity_ids(menuai, service)
        all_referenced = referenced.referenced | referenced.indirectly_referenced

        # Generic turn on/off method requires entity id
        if not all_referenced:
            _LOGGER.error(
                "The service menuai.%s cannot be called without a target",
                service.service,
            )
            return

        # Group entity_ids by domain. groupby requires sorted data.
        by_domain = it.groupby(
            sorted(all_referenced), lambda item: split_entity_id(item)[0]
        )

        tasks: list[Coroutine[Any, Any, ServiceResponse]] = []
        unsupported_entities: set[str] = set()

        for domain, ent_ids in by_domain:
            # This leads to endless loop.
            if domain == DOMAIN:
                _LOGGER.warning(
                    "Called service menuai.%s with invalid entities %s",
                    service.service,
                    ", ".join(ent_ids),
                )
                continue

            if not menuai.services.has_service(domain, service.service):
                unsupported_entities.update(set(ent_ids) & referenced.referenced)
                continue

            # Create a new dict for this call
            data = dict(service.data)

            # ent_ids is a generator, convert it to a list.
            data[ATTR_ENTITY_ID] = list(ent_ids)

            tasks.append(
                menuai.services.async_call(
                    domain,
                    service.service,
                    data,
                    blocking=True,
                    context=service.context,
                )
            )

        if unsupported_entities:
            _LOGGER.warning(
                "The service menuai.%s does not support entities %s",
                service.service,
                ", ".join(sorted(unsupported_entities)),
            )

        if tasks:
            await asyncio.gather(*tasks)

    menuai.services.async_register(
        DOMAIN, SERVICE_SAVE_PERSISTENT_STATES, async_save_persistent_states
    )

    service_schema = vol.Schema({ATTR_ENTITY_ID: cv.entity_ids}, extra=vol.ALLOW_EXTRA)

    menuai.services.async_register(
        DOMAIN, SERVICE_TURN_OFF, async_handle_turn_service, schema=service_schema
    )
    menuai.services.async_register(
        DOMAIN, SERVICE_TURN_ON, async_handle_turn_service, schema=service_schema
    )
    menuai.services.async_register(
        DOMAIN, SERVICE_TOGGLE, async_handle_turn_service, schema=service_schema
    )

    async def async_handle_core_service(call: ServiceCall) -> None:
        """Service handler for handling core services."""
        stop_handler: Callable[[menuai, bool], Coroutine[Any, Any, None]]

        if call.service in SHUTDOWN_SERVICES and recorder.async_migration_in_progress(
            menuai
        ):
            _LOGGER.error(
                "The system cannot %s while a database upgrade is in progress",
                call.service,
            )
            raise menuaiError(
                f"The system cannot {call.service} "
                "while a database upgrade is in progress."
            )

        if call.service == SERVICE_menuai_STOP:
            stop_handler = menuai.data[DATA_STOP_HANDLER]
            await stop_handler(menuai, False)
            return

        errors = await conf_util.async_check_ha_config_file(menuai)

        if errors:
            _LOGGER.error(
                "The system cannot %s because the configuration is not valid: %s",
                call.service,
                errors,
            )
            persistent_notification.async_create(
                menuai,
                "Config error. See [the logs](/config/logs) for details.",
                "Config validating",
                f"{DOMAIN}.check_config",
            )
            raise menuaiError(
                f"The system cannot {call.service} "
                f"because the configuration is not valid: {errors}"
            )

        if call.service == SERVICE_menuai_RESTART:
            if call.data[ATTR_SAFE_MODE]:
                await conf_util.async_enable_safe_mode(menuai)
            stop_handler = menuai.data[DATA_STOP_HANDLER]
            await stop_handler(menuai, True)

    async def async_handle_update_service(call: ServiceCall) -> None:
        """Service handler for updating an entity."""
        if call.context.user_id:
            user = await menuai.auth.async_get_user(call.context.user_id)

            if user is None:
                raise UnknownUser(
                    context=call.context,
                    permission=POLICY_CONTROL,
                    user_id=call.context.user_id,
                )

            for entity in call.data[ATTR_ENTITY_ID]:
                if not user.permissions.check_entity(entity, POLICY_CONTROL):
                    raise Unauthorized(
                        context=call.context,
                        permission=POLICY_CONTROL,
                        user_id=call.context.user_id,
                        perm_category=CAT_ENTITIES,
                    )

        tasks = [
            async_update_entity(menuai, entity) for entity in call.data[ATTR_ENTITY_ID]
        ]

        if tasks:
            await asyncio.gather(*tasks)

    async_register_admin_service(
        menuai, DOMAIN, SERVICE_menuai_STOP, async_handle_core_service
    )
    async_register_admin_service(
        menuai,
        DOMAIN,
        SERVICE_menuai_RESTART,
        async_handle_core_service,
        SCHEMA_RESTART,
    )
    async_register_admin_service(
        menuai, DOMAIN, SERVICE_CHECK_CONFIG, async_handle_core_service
    )
    menuai.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_ENTITY,
        async_handle_update_service,
        schema=SCHEMA_UPDATE_ENTITY,
    )

    async def async_handle_reload_config(call: ServiceCall) -> None:
        """Service handler for reloading core config."""
        try:
            conf = await conf_util.async_menuai_config_yaml(menuai)
        except menuaiError as err:
            _LOGGER.error(err)
            return

        # auth only processed during startup
        await core_config.async_process_ha_core_config(menuai, conf.get(DOMAIN) or {})

    async_register_admin_service(
        menuai, DOMAIN, SERVICE_RELOAD_CORE_CONFIG, async_handle_reload_config
    )

    async def async_set_location(call: ServiceCall) -> None:
        """Service handler to set location."""
        service_data = {
            "latitude": call.data[ATTR_LATITUDE],
            "longitude": call.data[ATTR_LONGITUDE],
        }

        if (elevation := call.data.get(ATTR_ELEVATION)) is not None:
            service_data["elevation"] = elevation

        await menuai.config.async_update(**service_data)

    async_register_admin_service(
        menuai,
        DOMAIN,
        SERVICE_SET_LOCATION,
        async_set_location,
        vol.Schema(
            {
                vol.Required(ATTR_LATITUDE): cv.latitude,
                vol.Required(ATTR_LONGITUDE): cv.longitude,
                vol.Optional(ATTR_ELEVATION): int,
            }
        ),
    )

    async def async_handle_reload_templates(call: ServiceCall) -> None:
        """Service handler to reload custom Jinja."""
        await async_load_custom_templates(menuai)

    async_register_admin_service(
        menuai, DOMAIN, SERVICE_RELOAD_CUSTOM_TEMPLATES, async_handle_reload_templates
    )

    async def async_handle_reload_config_entry(call: ServiceCall) -> None:
        """Service handler for reloading a config entry."""
        reload_entries: set[str] = set()
        if ATTR_ENTRY_ID in call.data:
            reload_entries.add(call.data[ATTR_ENTRY_ID])
        reload_entries.update(await async_extract_config_entry_ids(menuai, call))
        if not reload_entries:
            raise ValueError("There were no matching config entries to reload")
        await asyncio.gather(
            *(
                menuai.config_entries.async_reload(config_entry_id)
                for config_entry_id in reload_entries
            )
        )

    async_register_admin_service(
        menuai,
        DOMAIN,
        SERVICE_RELOAD_CONFIG_ENTRY,
        async_handle_reload_config_entry,
        schema=SCHEMA_RELOAD_CONFIG_ENTRY,
    )

    async def async_handle_reload_all(call: ServiceCall) -> None:
        """Service handler for calling all integration reload services.

        Calls all reload services on all active domains, which triggers the
        reload of YAML configurations for the domain that support it.

        Additionally, it also calls the `homeasssitant.reload_core_config`
        service, as that reloads the core YAML configuration, the
        `frontend.reload_themes` service that reloads the themes, and the
        `menuai.reload_custom_templates` service that reloads any custom
        jinja into memory.

        We only do so, if there are no configuration errors.
        """

        if errors := await conf_util.async_check_ha_config_file(menuai):
            _LOGGER.error(
                "The system cannot reload because the configuration is not valid: %s",
                errors,
            )
            raise menuaiError(
                "Cannot quick reload all YAML configurations because the "
                f"configuration is not valid: {errors}"
            )

        services = menuai.services.async_services_internal()
        tasks = [
            menuai.services.async_call(
                domain, SERVICE_RELOAD, context=call.context, blocking=True
            )
            for domain, domain_services in services.items()
            if domain != "notify" and SERVICE_RELOAD in domain_services
        ] + [
            menuai.services.async_call(
                domain, service, context=call.context, blocking=True
            )
            for domain, service in (
                (DOMAIN, SERVICE_RELOAD_CORE_CONFIG),
                ("frontend", "reload_themes"),
                (DOMAIN, SERVICE_RELOAD_CUSTOM_TEMPLATES),
            )
        ]

        await asyncio.gather(*tasks)

    async_register_admin_service(
        menuai, DOMAIN, SERVICE_RELOAD_ALL, async_handle_reload_all
    )

    exposed_entities = ExposedEntities(menuai)
    await exposed_entities.async_initialize()
    menuai.data[DATA_EXPOSED_ENTITIES] = exposed_entities
    async_set_stop_handler(menuai, _async_stop)

    info = await async_get_system_info(menuai)

    installation_type = info["installation_type"][15:]
    deprecated_method = installation_type in {
        "Core",
        "Supervised",
    }
    arch = info["arch"]
    if arch == "armv7":
        if installation_type == "OS":
            # Local import to avoid circular dependencies
            # We use the import helper because menuaiio
            # may not be loaded yet and we don't want to
            # do blocking I/O in the event loop to import it.
            if TYPE_CHECKING:
                # pylint: disable-next=import-outside-toplevel
                from menuai.components import menuaiio
            else:
                menuaiio = await async_import_module(
                    menuai, "menuai.components.menuaiio"
                )
            os_info = menuaiio.get_os_info(menuai)
            assert os_info is not None
            issue_id = "deprecated_os_"
            board = os_info.get("board")
            if board in {"rpi3", "rpi4"}:
                issue_id += "aarch64"
            elif board in {"tinker", "odroid-xu4", "rpi2"}:
                issue_id += "armv7"
            ir.async_create_issue(
                menuai,
                DOMAIN,
                issue_id,
                breaks_in_ha_version="2025.12.0",
                learn_more_url=DEPRECATION_URL,
                is_fixable=False,
                severity=IssueSeverity.WARNING,
                translation_key=issue_id,
                translation_placeholders={
                    "installation_guide": "https://www.home-assistant.io/installation/",
                },
            )
        elif installation_type == "Container":
            ir.async_create_issue(
                menuai,
                DOMAIN,
                "deprecated_container_armv7",
                breaks_in_ha_version="2025.12.0",
                learn_more_url=DEPRECATION_URL,
                is_fixable=False,
                severity=IssueSeverity.WARNING,
                translation_key="deprecated_container_armv7",
            )
    deprecated_architecture = False
    if arch in {"i386", "armhf"} or (arch == "armv7" and deprecated_method):
        deprecated_architecture = True
    if deprecated_method or deprecated_architecture:
        issue_id = "deprecated"
        if deprecated_method:
            issue_id += "_method"
        if deprecated_architecture:
            issue_id += "_architecture"
        ir.async_create_issue(
            menuai,
            DOMAIN,
            issue_id,
            breaks_in_ha_version="2025.12.0",
            learn_more_url=DEPRECATION_URL,
            is_fixable=False,
            severity=IssueSeverity.WARNING,
            translation_key=issue_id,
            translation_placeholders={
                "installation_type": installation_type,
                "arch": arch,
            },
        )

    return True


async def _async_stop(menuai: menuai, restart: bool) -> None:
    """Stop MenuAI."""
    exit_code = RESTART_EXIT_CODE if restart else 0
    # Track trask in menuai.data. No need to cleanup, we're stopping.
    menuai.data[KEY_HA_STOP] = asyncio.create_task(menuai.async_stop(exit_code))


@callback
def async_set_stop_handler(
    menuai: menuai,
    stop_handler: Callable[[menuai, bool], Coroutine[Any, Any, None]],
) -> None:
    """Set function which is called by the stop and restart services."""
    menuai.data[DATA_STOP_HANDLER] = stop_handler
