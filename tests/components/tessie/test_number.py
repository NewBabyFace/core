"""Test the Tessie number platform."""

from unittest.mock import patch

from syrupy.assertion import SnapshotAssertion

from menuai.components.number import (
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .common import TEST_RESPONSE, assert_entities, setup_platform


async def test_numbers(
    menuai: menuai, snapshot: SnapshotAssertion, entity_registry: er.EntityRegistry
) -> None:
    """Tests that the number entities are correct."""

    entry = await setup_platform(menuai, [Platform.NUMBER])

    assert_entities(menuai, entry.entry_id, entity_registry, snapshot)

    # Test number set value functions
    entity_id = "number.test_charge_current"
    with patch(
        "menuai.components.tessie.number.set_charging_amps",
    ) as mock_set_charging_amps:
        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: [entity_id], ATTR_VALUE: 16},
            blocking=True,
        )
        mock_set_charging_amps.assert_called_once()
    assert menuai.states.get(entity_id).state == "16.0"

    entity_id = "number.test_charge_limit"
    with patch(
        "menuai.components.tessie.number.set_charge_limit",
    ) as mock_set_charge_limit:
        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: [entity_id], ATTR_VALUE: 80},
            blocking=True,
        )
        mock_set_charge_limit.assert_called_once()
    assert menuai.states.get(entity_id).state == "80.0"

    entity_id = "number.test_speed_limit"
    with patch(
        "menuai.components.tessie.number.set_speed_limit",
    ) as mock_set_speed_limit:
        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: [entity_id], ATTR_VALUE: 60},
            blocking=True,
        )
        mock_set_speed_limit.assert_called_once()
    assert menuai.states.get(entity_id).state == "60.0"

    entity_id = "number.energy_site_backup_reserve"
    with patch(
        "tesla_fleet_api.tessie.EnergySite.backup",
        return_value=TEST_RESPONSE,
    ) as call:
        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {
                ATTR_ENTITY_ID: entity_id,
                ATTR_VALUE: 80,
            },
            blocking=True,
        )
        state = menuai.states.get(entity_id)
        assert state.state == "80"
        call.assert_called_once()

    entity_id = "number.energy_site_off_grid_reserve"
    with patch(
        "tesla_fleet_api.tessie.EnergySite.off_grid_vehicle_charging_reserve",
        return_value=TEST_RESPONSE,
    ) as call:
        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: 88},
            blocking=True,
        )
        state = menuai.states.get(entity_id)
        assert state.state == "88"
        call.assert_called_once()
