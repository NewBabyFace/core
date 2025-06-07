"""The test for the Yale Smart ALarm button platform."""

from __future__ import annotations

from unittest.mock import Mock

from freezegun import freeze_time
import pytest
from syrupy.assertion import SnapshotAssertion
from yalesmartalarmclient.exceptions import UnknownError

from menuai.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry, snapshot_platform


@freeze_time("2024-04-29T18:00:00.612351+00:00")
@pytest.mark.parametrize(
    "load_platforms",
    [[Platform.BUTTON]],
)
async def test_button(
    menuai: menuai,
    load_config_entry: tuple[MockConfigEntry, Mock],
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the Yale Smart Alarm button."""
    entry = load_config_entry[0]
    client = load_config_entry[1]
    client.trigger_panic_button = Mock(return_value=True)
    await menuai.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {
            ATTR_ENTITY_ID: "button.test_username_panic_button",
        },
        blocking=True,
    )
    await snapshot_platform(menuai, entity_registry, snapshot, entry.entry_id)
    client.trigger_panic_button.assert_called_once()
    client.trigger_panic_button.reset_mock()
    client.trigger_panic_button = Mock(side_effect=UnknownError("test_side_effect"))
    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {
                ATTR_ENTITY_ID: "button.test_username_panic_button",
            },
            blocking=True,
        )
    client.trigger_panic_button.assert_called_once()
