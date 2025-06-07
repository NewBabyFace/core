"""Test the Advantage Air Update Platform."""

from unittest.mock import AsyncMock

from menuai.components.advantage_air.const import DOMAIN
from menuai.const import STATE_ON
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import add_mock_config

from tests.common import load_json_object_fixture

TEST_NEEDS_UPDATE = load_json_object_fixture("needsUpdate.json", DOMAIN)


async def test_update_platform(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    mock_get: AsyncMock,
) -> None:
    """Test update platform."""
    mock_get.return_value = TEST_NEEDS_UPDATE
    await add_mock_config(menuai)

    entity_id = "update.testname_app"
    state = menuai.states.get(entity_id)
    assert state
    assert state.state == STATE_ON

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.unique_id == "uniqueid"
