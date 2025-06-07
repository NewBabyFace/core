"""Test Roborock Time platform."""

from datetime import time
from unittest.mock import Mock

import pytest
import roborock

from menuai.components.time import SERVICE_SET_VALUE
from menuai.const import Platform
from menuai.core import menuai
from menuai.exceptions import menuaiError

from tests.common import MockConfigEntry


@pytest.fixture
def platforms() -> list[Platform]:
    """Fixture to set platforms used in the test."""
    return [Platform.TIME]


@pytest.mark.parametrize(
    ("entity_id"),
    [
        ("time.roborock_s7_maxv_do_not_disturb_begin"),
        ("time.roborock_s7_maxv_do_not_disturb_end"),
    ],
)
async def test_update_success(
    menuai: menuai,
    mock_send_message: Mock,
    bypass_api_fixture,
    setup_entry: MockConfigEntry,
    entity_id: str,
) -> None:
    """Test turning switch entities on and off."""
    # Ensure that the entity exist, as these test can pass even if there is no entity.
    assert menuai.states.get(entity_id) is not None
    await menuai.services.async_call(
        "time",
        SERVICE_SET_VALUE,
        service_data={"time": time(hour=1, minute=1)},
        blocking=True,
        target={"entity_id": entity_id},
    )
    assert mock_send_message.assert_called_once


@pytest.mark.parametrize(
    ("entity_id"),
    [
        ("time.roborock_s7_maxv_do_not_disturb_begin"),
    ],
)
@pytest.mark.parametrize(
    "send_message_side_effect", [roborock.exceptions.RoborockTimeout]
)
async def test_update_failure(
    menuai: menuai,
    mock_send_message: Mock,
    bypass_api_fixture,
    setup_entry: MockConfigEntry,
    entity_id: str,
) -> None:
    """Test turning switch entities on and off."""
    # Ensure that the entity exist, as these test can pass even if there is no entity.
    assert menuai.states.get(entity_id) is not None
    with pytest.raises(menuaiError, match="Failed to update Roborock options"):
        await menuai.services.async_call(
            "time",
            SERVICE_SET_VALUE,
            service_data={"time": time(hour=1, minute=1)},
            blocking=True,
            target={"entity_id": entity_id},
        )
    assert mock_send_message.assert_called_once
