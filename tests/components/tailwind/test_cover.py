"""Tests for cover entities provided by the Tailwind integration."""

from unittest.mock import ANY, MagicMock

from gotailwind import (
    TailwindDoorAlreadyInStateError,
    TailwindDoorDisabledError,
    TailwindDoorLockedOutError,
    TailwindDoorOperationCommand,
    TailwindError,
)
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.cover import (
    DOMAIN as COVER_DOMAIN,
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
)
from menuai.components.tailwind.const import DOMAIN
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import device_registry as dr, entity_registry as er

pytestmark = pytest.mark.usefixtures("init_integration")


@pytest.mark.parametrize(
    "entity_id",
    [
        "cover.door_1",
        "cover.door_2",
    ],
)
async def test_cover_entities(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    entity_id: str,
) -> None:
    """Test cover entities provided by the Tailwind integration."""
    assert (state := menuai.states.get(entity_id))
    assert state == snapshot

    assert (entity_entry := entity_registry.async_get(state.entity_id))
    assert entity_entry == snapshot

    assert entity_entry.device_id
    assert (device_entry := device_registry.async_get(entity_entry.device_id))
    assert device_entry == snapshot


async def test_cover_operations(
    menuai: menuai,
    mock_tailwind: MagicMock,
) -> None:
    """Test operating the doors."""
    assert len(mock_tailwind.operate.mock_calls) == 0
    await menuai.services.async_call(
        COVER_DOMAIN,
        SERVICE_OPEN_COVER,
        {
            ATTR_ENTITY_ID: "cover.door_1",
        },
        blocking=True,
    )

    mock_tailwind.operate.assert_called_with(
        door=ANY, operation=TailwindDoorOperationCommand.OPEN
    )

    await menuai.services.async_call(
        COVER_DOMAIN,
        SERVICE_CLOSE_COVER,
        {
            ATTR_ENTITY_ID: "cover.door_1",
        },
        blocking=True,
    )

    mock_tailwind.operate.assert_called_with(
        door=ANY, operation=TailwindDoorOperationCommand.CLOSE
    )

    # Test door disabled error handling
    mock_tailwind.operate.side_effect = TailwindDoorDisabledError("Door disabled")

    with pytest.raises(menuaiError) as excinfo:
        await menuai.services.async_call(
            COVER_DOMAIN,
            SERVICE_OPEN_COVER,
            {
                ATTR_ENTITY_ID: "cover.door_1",
            },
            blocking=True,
        )
    assert str(excinfo.value) == "The door is disabled and cannot be operated"

    assert excinfo.value.translation_domain == DOMAIN
    assert excinfo.value.translation_key == "door_disabled"

    with pytest.raises(menuaiError) as excinfo:
        await menuai.services.async_call(
            COVER_DOMAIN,
            SERVICE_CLOSE_COVER,
            {
                ATTR_ENTITY_ID: "cover.door_1",
            },
            blocking=True,
        )

    assert str(excinfo.value) == "The door is disabled and cannot be operated"
    assert excinfo.value.translation_domain == DOMAIN
    assert excinfo.value.translation_key == "door_disabled"

    # Test door locked out error handling
    mock_tailwind.operate.side_effect = TailwindDoorLockedOutError("Door locked out")

    with pytest.raises(menuaiError) as excinfo:
        await menuai.services.async_call(
            COVER_DOMAIN,
            SERVICE_OPEN_COVER,
            {
                ATTR_ENTITY_ID: "cover.door_1",
            },
            blocking=True,
        )

    assert str(excinfo.value) == "The door is locked out and cannot be operated"
    assert excinfo.value.translation_domain == DOMAIN
    assert excinfo.value.translation_key == "door_locked_out"

    with pytest.raises(menuaiError) as excinfo:
        await menuai.services.async_call(
            COVER_DOMAIN,
            SERVICE_CLOSE_COVER,
            {
                ATTR_ENTITY_ID: "cover.door_1",
            },
            blocking=True,
        )

    assert str(excinfo.value) == "The door is locked out and cannot be operated"
    assert excinfo.value.translation_domain == DOMAIN
    assert excinfo.value.translation_key == "door_locked_out"

    # Test door error handling
    mock_tailwind.operate.side_effect = TailwindError("Some error")

    with pytest.raises(menuaiError) as excinfo:
        await menuai.services.async_call(
            COVER_DOMAIN,
            SERVICE_OPEN_COVER,
            {
                ATTR_ENTITY_ID: "cover.door_1",
            },
            blocking=True,
        )

    assert (
        str(excinfo.value)
        == "An error occurred while communicating with the Tailwind device"
    )
    assert excinfo.value.translation_domain == DOMAIN
    assert excinfo.value.translation_key == "communication_error"

    with pytest.raises(menuaiError) as excinfo:
        await menuai.services.async_call(
            COVER_DOMAIN,
            SERVICE_CLOSE_COVER,
            {
                ATTR_ENTITY_ID: "cover.door_1",
            },
            blocking=True,
        )

    assert (
        str(excinfo.value)
        == "An error occurred while communicating with the Tailwind device"
    )
    assert excinfo.value.translation_domain == DOMAIN
    assert excinfo.value.translation_key == "communication_error"

    # Test door already in state
    mock_tailwind.operate.side_effect = TailwindDoorAlreadyInStateError(
        "Door is already in the requested state"
    )

    # This call should not raise an exception
    await menuai.services.async_call(
        COVER_DOMAIN,
        SERVICE_OPEN_COVER,
        {
            ATTR_ENTITY_ID: "cover.door_1",
        },
        blocking=True,
    )

    # This call should not raise an exception
    await menuai.services.async_call(
        COVER_DOMAIN,
        SERVICE_CLOSE_COVER,
        {
            ATTR_ENTITY_ID: "cover.door_1",
        },
        blocking=True,
    )
