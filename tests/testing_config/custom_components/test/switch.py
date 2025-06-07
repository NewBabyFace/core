"""Stub switch platform for translation tests."""

from menuai.core import menuai
from menuai.helpers.entity_platform import AddEntitiesCallback
from menuai.helpers.typing import ConfigType, DiscoveryInfoType


async def async_setup_platform(
    menuai: menuai,
    config: ConfigType,
    async_add_entities_callback: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Stub setup for translation tests."""
    async_add_entities_callback([])
