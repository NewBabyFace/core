"""Tests for the litejet component."""

from menuai.components import scene, switch
from menuai.components.litejet import DOMAIN
from menuai.const import CONF_PORT
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry


async def async_init_integration(
    menuai: menuai, use_switch: bool = False, use_scene: bool = False
) -> MockConfigEntry:
    """Set up the LiteJet integration in MenuAI."""

    registry = er.async_get(menuai)

    entry_data = {CONF_PORT: "/dev/mock"}

    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=entry_data[CONF_PORT], data=entry_data
    )

    if use_switch:
        registry.async_get_or_create(
            switch.DOMAIN,
            DOMAIN,
            f"{entry.entry_id}_1",
            suggested_object_id="mock_switch_1",
            disabled_by=None,
        )
        registry.async_get_or_create(
            switch.DOMAIN,
            DOMAIN,
            f"{entry.entry_id}_2",
            suggested_object_id="mock_switch_2",
            disabled_by=None,
        )

    if use_scene:
        registry.async_get_or_create(
            scene.DOMAIN,
            DOMAIN,
            f"{entry.entry_id}_1",
            suggested_object_id="litejet_mock_scene_1",
            disabled_by=None,
        )

    entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    return entry
