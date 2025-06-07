"""Basic checks for entity map storage."""

from collections.abc import Callable
from typing import Any

from aiohomekit.model import Accessory
from aiohomekit.model.characteristics import CharacteristicsTypes
from aiohomekit.model.services import ServicesTypes

from menuai.components.homekit_controller.const import ENTITY_MAP
from menuai.components.homekit_controller.storage import EntityMapStorage
from menuai.core import menuai

from .common import setup_platform, setup_test_component

from tests.common import flush_store


async def test_load_from_storage(
    menuai: menuai, menuai_storage: dict[str, Any]
) -> None:
    """Test that entity map can be correctly loaded from cache."""
    hkid = "00:00:00:00:00:00"

    menuai_storage["homekit_controller-entity-map"] = {
        "version": 1,
        "data": {"pairings": {hkid: {"c#": 1, "accessories": []}}},
    }

    await setup_platform(menuai)
    assert hkid in menuai.data[ENTITY_MAP].storage_data


async def test_storage_is_removed(
    menuai: menuai, menuai_storage: dict[str, Any]
) -> None:
    """Test entity map storage removal is idempotent."""
    await setup_platform(menuai)

    entity_map = menuai.data[ENTITY_MAP]
    hkid = "00:00:00:00:00:01"

    entity_map.async_create_or_update_map(hkid, 1, [])
    assert hkid in entity_map.storage_data
    await flush_store(entity_map.store)
    assert hkid in menuai_storage[ENTITY_MAP]["data"]["pairings"]

    entity_map.async_delete_map(hkid)
    assert hkid not in menuai.data[ENTITY_MAP].storage_data
    await flush_store(entity_map.store)

    assert menuai_storage[ENTITY_MAP]["data"]["pairings"] == {}


async def test_storage_is_removed_idempotent(menuai: menuai) -> None:
    """Test entity map storage removal is idempotent."""
    await setup_platform(menuai)

    entity_map = menuai.data[ENTITY_MAP]
    hkid = "00:00:00:00:00:01"

    assert hkid not in entity_map.storage_data

    entity_map.async_delete_map(hkid)

    assert hkid not in entity_map.storage_data


def create_lightbulb_service(accessory: Accessory) -> None:
    """Define lightbulb characteristics."""
    service = accessory.add_service(ServicesTypes.LIGHTBULB)
    on_char = service.add_char(CharacteristicsTypes.ON)
    on_char.value = 0


async def test_storage_is_updated_on_add(
    menuai: menuai, menuai_storage: dict[str, Any], get_next_aid: Callable[[], int]
) -> None:
    """Test entity map storage is cleaned up on adding an accessory."""
    await setup_test_component(menuai, get_next_aid(), create_lightbulb_service)

    entity_map: EntityMapStorage = menuai.data[ENTITY_MAP]
    hkid = "00:00:00:00:00:00"

    # Is in memory store updated?
    assert hkid in entity_map.storage_data

    # Is saved out to store?
    await flush_store(entity_map.store)
    assert hkid in menuai_storage[ENTITY_MAP]["data"]["pairings"]
