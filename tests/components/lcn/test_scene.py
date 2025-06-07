"""Test for the LCN scene platform."""

from unittest.mock import patch

from pypck.lcn_defs import OutputPort, RelayPort
from syrupy.assertion import SnapshotAssertion

from menuai.components.scene import DOMAIN as DOMAIN_SCENE
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_ON,
    STATE_UNAVAILABLE,
    Platform,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .conftest import MockConfigEntry, MockModuleConnection, init_integration

from tests.common import snapshot_platform


async def test_setup_lcn_scene(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the setup of switch."""
    with patch("menuai.components.lcn.PLATFORMS", [Platform.SCENE]):
        await init_integration(menuai, entry)

    await snapshot_platform(menuai, entity_registry, snapshot, entry.entry_id)


async def test_scene_activate(
    menuai: menuai,
    entry: MockConfigEntry,
) -> None:
    """Test the scene is activated."""
    await init_integration(menuai, entry)
    with patch.object(MockModuleConnection, "activate_scene") as activate_scene:
        await menuai.services.async_call(
            DOMAIN_SCENE,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: "scene.testmodule_romantic"},
            blocking=True,
        )

    state = menuai.states.get("scene.testmodule_romantic")
    assert state is not None

    activate_scene.assert_awaited_with(
        0, 0, [OutputPort.OUTPUT1, OutputPort.OUTPUT2], [RelayPort.RELAY1], 0.0
    )


async def test_unload_config_entry(menuai: menuai, entry: MockConfigEntry) -> None:
    """Test the scene is removed when the config entry is unloaded."""
    await init_integration(menuai, entry)

    await menuai.config_entries.async_unload(entry.entry_id)
    state = menuai.states.get("scene.testmodule_romantic")
    assert state.state == STATE_UNAVAILABLE
