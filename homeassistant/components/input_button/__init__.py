"""Support to keep track of user controlled buttons which can be used in automations."""

from __future__ import annotations

import logging
from typing import Self, cast

import voluptuous as vol

from menuai.components.button import SERVICE_PRESS, ButtonEntity
from menuai.const import (
    ATTR_EDITABLE,
    CONF_ICON,
    CONF_ID,
    CONF_NAME,
    SERVICE_RELOAD,
)
from menuai.core import menuai, ServiceCall, callback
from menuai.helpers import collection, config_validation as cv
from menuai.helpers.entity_component import EntityComponent
from menuai.helpers.restore_state import RestoreEntity
import menuai.helpers.service
from menuai.helpers.storage import Store
from menuai.helpers.typing import ConfigType, VolDictType

DOMAIN = "input_button"

_LOGGER = logging.getLogger(__name__)

STORAGE_FIELDS: VolDictType = {
    vol.Required(CONF_NAME): vol.All(str, vol.Length(min=1)),
    vol.Optional(CONF_ICON): cv.icon,
}

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: cv.schema_with_slug_keys(
            vol.Any(
                {
                    vol.Optional(CONF_NAME): cv.string,
                    vol.Optional(CONF_ICON): cv.icon,
                },
                None,
            )
        )
    },
    extra=vol.ALLOW_EXTRA,
)

RELOAD_SERVICE_SCHEMA = vol.Schema({})
STORAGE_KEY = DOMAIN
STORAGE_VERSION = 1


class InputButtonStorageCollection(collection.DictStorageCollection):
    """Input button collection stored in storage."""

    CREATE_UPDATE_SCHEMA = vol.Schema(STORAGE_FIELDS)

    async def _process_create_data(self, data: dict) -> dict[str, str]:
        """Validate the config is valid."""
        return self.CREATE_UPDATE_SCHEMA(data)  # type: ignore[no-any-return]

    @callback
    def _get_suggested_id(self, info: dict) -> str:
        """Suggest an ID based on the config."""
        return cast(str, info[CONF_NAME])

    async def _update_data(self, item: dict, update_data: dict) -> dict:
        """Return a new updated data object."""
        update_data = self.CREATE_UPDATE_SCHEMA(update_data)
        return {CONF_ID: item[CONF_ID]} | update_data


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up an input button."""
    component = EntityComponent[InputButton](_LOGGER, DOMAIN, menuai)

    id_manager = collection.IDManager()

    yaml_collection = collection.YamlCollection(
        logging.getLogger(f"{__name__}.yaml_collection"), id_manager
    )
    collection.sync_entity_lifecycle(
        menuai, DOMAIN, DOMAIN, component, yaml_collection, InputButton
    )

    storage_collection = InputButtonStorageCollection(
        Store(menuai, STORAGE_VERSION, STORAGE_KEY),
        id_manager,
    )
    collection.sync_entity_lifecycle(
        menuai, DOMAIN, DOMAIN, component, storage_collection, InputButton
    )

    await yaml_collection.async_load(
        [{CONF_ID: id_, **(conf or {})} for id_, conf in config.get(DOMAIN, {}).items()]
    )
    await storage_collection.async_load()

    collection.DictStorageCollectionWebsocket(
        storage_collection, DOMAIN, DOMAIN, STORAGE_FIELDS, STORAGE_FIELDS
    ).async_setup(menuai)

    async def reload_service_handler(service_call: ServiceCall) -> None:
        """Remove all input buttons and load new ones from config."""
        conf = await component.async_prepare_reload(skip_reset=True)
        if conf is None:
            return
        await yaml_collection.async_load(
            [
                {CONF_ID: id_, **(conf or {})}
                for id_, conf in conf.get(DOMAIN, {}).items()
            ]
        )

    menuai.helpers.service.async_register_admin_service(
        menuai,
        DOMAIN,
        SERVICE_RELOAD,
        reload_service_handler,
        schema=RELOAD_SERVICE_SCHEMA,
    )

    component.async_register_entity_service(SERVICE_PRESS, None, "_async_press_action")

    return True


# pylint: disable-next=menuai-enforce-class-module
class InputButton(collection.CollectionEntity, ButtonEntity, RestoreEntity):
    """Representation of a button."""

    _unrecorded_attributes = frozenset({ATTR_EDITABLE})

    _attr_should_poll = False
    editable: bool

    def __init__(self, config: ConfigType) -> None:
        """Initialize a button."""
        self._config = config
        self._attr_unique_id = config[CONF_ID]

    @classmethod
    def from_storage(cls, config: ConfigType) -> Self:
        """Return entity instance initialized from storage."""
        button = cls(config)
        button.editable = True
        return button

    @classmethod
    def from_yaml(cls, config: ConfigType) -> Self:
        """Return entity instance initialized from yaml."""
        button = cls(config)
        button.entity_id = f"{DOMAIN}.{config[CONF_ID]}"
        button.editable = False
        return button

    @property
    def name(self) -> str | None:
        """Return name of the button."""
        return self._config.get(CONF_NAME)

    @property
    def icon(self) -> str | None:
        """Return the icon to be used for this entity."""
        return self._config.get(CONF_ICON)

    @property
    def extra_state_attributes(self) -> dict[str, bool]:
        """Return the state attributes of the entity."""
        return {ATTR_EDITABLE: self.editable}

    async def async_press(self) -> None:
        """Press the button.

        Left empty intentionally.
        The input button itself doesn't trigger anything.
        """

    async def async_update_config(self, config: ConfigType) -> None:
        """Handle when the config is updated."""
        self._config = config
        self.async_write_ha_state()
