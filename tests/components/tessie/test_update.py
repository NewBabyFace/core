"""Test the Tessie update platform."""

from unittest.mock import patch

from syrupy.assertion import SnapshotAssertion

from menuai.components.update import (
    ATTR_IN_PROGRESS,
    DOMAIN as UPDATE_DOMAIN,
    SERVICE_INSTALL,
)
from menuai.const import ATTR_ENTITY_ID, STATE_ON, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .common import assert_entities, setup_platform


async def test_updates(
    menuai: menuai, snapshot: SnapshotAssertion, entity_registry: er.EntityRegistry
) -> None:
    """Tests that update entity is correct."""

    entry = await setup_platform(menuai, [Platform.UPDATE])

    assert_entities(menuai, entry.entry_id, entity_registry, snapshot)

    entity_id = "update.test_update"

    with patch(
        "menuai.components.tessie.update.schedule_software_update"
    ) as mock_update:
        await menuai.services.async_call(
            UPDATE_DOMAIN,
            SERVICE_INSTALL,
            {ATTR_ENTITY_ID: [entity_id]},
            blocking=True,
        )
        mock_update.assert_called_once()

    state = menuai.states.get(entity_id)
    assert state.state == STATE_ON
    assert state.attributes.get(ATTR_IN_PROGRESS) == 1
