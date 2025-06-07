"""Test the Honeywell humidity domain."""

from unittest.mock import MagicMock

from syrupy.assertion import SnapshotAssertion

from menuai.components.humidifier import (
    ATTR_HUMIDITY,
    DOMAIN as HUMIDIFIER_DOMAIN,
    SERVICE_SET_HUMIDITY,
)
from menuai.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF, SERVICE_TURN_ON
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import init_integration


async def test_humidifier_service_calls(
    menuai: menuai, device: MagicMock, config_entry: MagicMock
) -> None:
    """Test the setup of the climate entities when there are no additional options available."""
    device.has_humidifier = True
    await init_integration(menuai, config_entry)
    entity_id = f"humidifier.{device.name}_humidifier"
    assert menuai.states.get(f"humidifier.{device.name}_dehumidifier") is None

    await menuai.services.async_call(
        HUMIDIFIER_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    device.set_humidifier_auto.assert_called_once()

    await menuai.services.async_call(
        HUMIDIFIER_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    device.set_humidifier_off.assert_called_once()

    await menuai.services.async_call(
        HUMIDIFIER_DOMAIN,
        SERVICE_SET_HUMIDITY,
        {ATTR_ENTITY_ID: entity_id, ATTR_HUMIDITY: 40},
        blocking=True,
    )
    device.set_humidifier_setpoint.assert_called_once_with(40)


async def test_dehumidifier_service_calls(
    menuai: menuai, device: MagicMock, config_entry: MagicMock
) -> None:
    """Test the setup of the climate entities when there are no additional options available."""
    device.has_dehumidifier = True
    await init_integration(menuai, config_entry)
    entity_id = f"humidifier.{device.name}_dehumidifier"
    assert menuai.states.get(f"humidifier.{device.name}_humidifier") is None

    await menuai.services.async_call(
        HUMIDIFIER_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    device.set_dehumidifier_auto.assert_called_once()

    await menuai.services.async_call(
        HUMIDIFIER_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    device.set_dehumidifier_off.assert_called_once()

    await menuai.services.async_call(
        HUMIDIFIER_DOMAIN,
        SERVICE_SET_HUMIDITY,
        {ATTR_ENTITY_ID: entity_id, ATTR_HUMIDITY: 40},
        blocking=True,
    )
    device.set_dehumidifier_setpoint.assert_called_once_with(40)


async def test_static_attributes(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    device: MagicMock,
    config_entry: MagicMock,
    snapshot: SnapshotAssertion,
) -> None:
    """Test static humidifier attributes."""
    device.has_dehumidifier = True
    device.has_humidifier = True
    await init_integration(menuai, config_entry)

    entity_id_dehumidifier = f"humidifier.{device.name}_dehumidifier"
    entity_id_humidifier = f"humidifier.{device.name}_humidifier"
    entry = entity_registry.async_get(entity_id_dehumidifier)
    assert entry

    state = menuai.states.get(entity_id_dehumidifier)

    assert state == snapshot(name="dehumidifier")

    state = menuai.states.get(entity_id_humidifier)

    assert state == snapshot(name="humidifier")
