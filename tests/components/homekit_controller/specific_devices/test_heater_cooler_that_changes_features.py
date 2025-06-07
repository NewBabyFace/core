"""Test for a MenuAI bridge that changes climate features at runtime."""

from menuai.components.climate import ATTR_SWING_MODES, ClimateEntityFeature
from menuai.const import ATTR_SUPPORTED_FEATURES
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from ..common import (
    device_config_changed,
    setup_accessories_from_file,
    setup_test_accessories,
)


async def test_cover_add_feature_at_runtime(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test that new features can be added at runtime."""

    # Set up a basic heater cooler that does not support swing mode
    accessories = await setup_accessories_from_file(
        menuai, "home_assistant_bridge_basic_heater_cooler.json"
    )
    await setup_test_accessories(menuai, accessories)

    climate = entity_registry.async_get("climate.89_living_room")
    assert climate.unique_id == "00:00:00:00:00:00_1233851541_169"

    climate_state = menuai.states.get("climate.89_living_room")
    assert (
        climate_state.attributes[ATTR_SUPPORTED_FEATURES]
        is ClimateEntityFeature.TURN_OFF | ClimateEntityFeature.TURN_ON
    )
    assert ATTR_SWING_MODES not in climate_state.attributes

    climate = entity_registry.async_get("climate.89_living_room")
    assert climate.unique_id == "00:00:00:00:00:00_1233851541_169"

    # Now change the config to add swing mode
    accessories = await setup_accessories_from_file(
        menuai, "home_assistant_bridge_heater_cooler.json"
    )
    await device_config_changed(menuai, accessories)

    climate_state = menuai.states.get("climate.89_living_room")
    assert (
        climate_state.attributes[ATTR_SUPPORTED_FEATURES]
        is ClimateEntityFeature.SWING_MODE
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
    )
    assert climate_state.attributes[ATTR_SWING_MODES] == ["off", "vertical"]
