"""Support for KNX scenes."""

from __future__ import annotations

from typing import Any

from xknx.devices import Scene as XknxScene

from menuai import config_entries
from menuai.components.scene import Scene
from menuai.const import CONF_ENTITY_CATEGORY, CONF_NAME, Platform
from menuai.core import menuai
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback
from menuai.helpers.typing import ConfigType

from . import KNXModule
from .const import KNX_ADDRESS, KNX_MODULE_KEY
from .entity import KnxYamlEntity
from .schema import SceneSchema


async def async_setup_entry(
    menuai: menuai,
    config_entry: config_entries.ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up scene(s) for KNX platform."""
    knx_module = menuai.data[KNX_MODULE_KEY]
    config: list[ConfigType] = knx_module.config_yaml[Platform.SCENE]

    async_add_entities(KNXScene(knx_module, entity_config) for entity_config in config)


class KNXScene(KnxYamlEntity, Scene):
    """Representation of a KNX scene."""

    _device: XknxScene

    def __init__(self, knx_module: KNXModule, config: ConfigType) -> None:
        """Init KNX scene."""
        super().__init__(
            knx_module=knx_module,
            device=XknxScene(
                xknx=knx_module.xknx,
                name=config[CONF_NAME],
                group_address=config[KNX_ADDRESS],
                scene_number=config[SceneSchema.CONF_SCENE_NUMBER],
            ),
        )
        self._attr_entity_category = config.get(CONF_ENTITY_CATEGORY)
        self._attr_unique_id = (
            f"{self._device.scene_value.group_address}_{self._device.scene_number}"
        )

    async def async_activate(self, **kwargs: Any) -> None:
        """Activate the scene."""
        await self._device.run()
