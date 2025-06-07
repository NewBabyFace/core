"""Test Roborock Number platform."""

from unittest.mock import patch

import pytest
import roborock

from menuai.components.number import ATTR_VALUE, SERVICE_SET_VALUE
from menuai.const import Platform
from menuai.core import menuai
from menuai.exceptions import menuaiError

from tests.common import MockConfigEntry


@pytest.fixture
def platforms() -> list[Platform]:
    """Fixture to set platforms used in the test."""
    return [Platform.NUMBER]


@pytest.mark.parametrize(
    ("entity_id", "value"),
    [
        ("number.roborock_s7_maxv_volume", 3.0),
    ],
)
async def test_update_success(
    menuai: menuai,
    bypass_api_fixture,
    setup_entry: MockConfigEntry,
    entity_id: str,
    value: float,
) -> None:
    """Test allowed changing values for number entities."""
    # Ensure that the entity exist, as these test can pass even if there is no entity.
    assert menuai.states.get(entity_id) is not None
    with patch(
        "menuai.components.roborock.coordinator.RoborockLocalClientV1.send_message"
    ) as mock_send_message:
        await menuai.services.async_call(
            "number",
            SERVICE_SET_VALUE,
            service_data={ATTR_VALUE: value},
            blocking=True,
            target={"entity_id": entity_id},
        )
    assert mock_send_message.assert_called_once


@pytest.mark.parametrize(
    ("entity_id", "value"),
    [
        ("number.roborock_s7_maxv_volume", 3.0),
    ],
)
async def test_update_failed(
    menuai: menuai,
    bypass_api_fixture,
    setup_entry: MockConfigEntry,
    entity_id: str,
    value: float,
) -> None:
    """Test allowed changing values for number entities."""
    # Ensure that the entity exist, as these test can pass even if there is no entity.
    assert menuai.states.get(entity_id) is not None
    with (
        patch(
            "menuai.components.roborock.coordinator.RoborockLocalClientV1.send_message",
            side_effect=roborock.exceptions.RoborockTimeout,
        ) as mock_send_message,
        pytest.raises(menuaiError, match="Failed to update Roborock options"),
    ):
        await menuai.services.async_call(
            "number",
            SERVICE_SET_VALUE,
            service_data={ATTR_VALUE: value},
            blocking=True,
            target={"entity_id": entity_id},
        )
    assert mock_send_message.assert_called_once
