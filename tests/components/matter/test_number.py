"""Test Matter number entities."""

from unittest.mock import MagicMock, call

from matter_server.client.models.node import MatterNode
from matter_server.common import custom_clusters
from matter_server.common.errors import MatterError
from matter_server.common.helpers.util import create_attribute_path_from_attribute
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.const import Platform
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er

from .common import (
    set_node_attribute,
    snapshot_matter_entities,
    trigger_subscription_callback,
)


@pytest.mark.usefixtures("matter_devices")
async def test_numbers(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test numbers."""
    snapshot_matter_entities(menuai, entity_registry, snapshot, Platform.NUMBER)


@pytest.mark.parametrize("node_fixture", ["dimmable_light"])
async def test_level_control_config_entities(
    menuai: menuai,
    matter_client: MagicMock,
    matter_node: MatterNode,
) -> None:
    """Test number entities are created for the LevelControl cluster (config) attributes."""
    state = menuai.states.get("number.mock_dimmable_light_on_level")
    assert state
    assert state.state == "255"

    state = menuai.states.get("number.mock_dimmable_light_on_transition_time")
    assert state
    assert state.state == "0.0"

    state = menuai.states.get("number.mock_dimmable_light_off_transition_time")
    assert state
    assert state.state == "0.0"

    state = menuai.states.get("number.mock_dimmable_light_on_off_transition_time")
    assert state
    assert state.state == "0.0"

    set_node_attribute(matter_node, 1, 0x00000008, 0x0011, 20)
    await trigger_subscription_callback(menuai, matter_client)

    state = menuai.states.get("number.mock_dimmable_light_on_level")
    assert state
    assert state.state == "20"


@pytest.mark.parametrize("node_fixture", ["eve_weather_sensor"])
async def test_eve_weather_sensor_altitude(
    menuai: menuai,
    matter_client: MagicMock,
    matter_node: MatterNode,
) -> None:
    """Test weather sensor created from (Eve) custom cluster."""
    # pressure sensor on Eve custom cluster
    state = menuai.states.get("number.eve_weather_altitude_above_sea_level")
    assert state
    assert state.state == "40.0"

    set_node_attribute(matter_node, 1, 319486977, 319422483, 800)
    await trigger_subscription_callback(menuai, matter_client)
    state = menuai.states.get("number.eve_weather_altitude_above_sea_level")
    assert state
    assert state.state == "800.0"

    # test set value
    await menuai.services.async_call(
        "number",
        "set_value",
        {
            "entity_id": "number.eve_weather_altitude_above_sea_level",
            "value": 500,
        },
        blocking=True,
    )
    assert matter_client.write_attribute.call_count == 1
    assert matter_client.write_attribute.call_args_list[0] == call(
        node_id=matter_node.node_id,
        attribute_path=create_attribute_path_from_attribute(
            endpoint_id=1,
            attribute=custom_clusters.EveCluster.Attributes.Altitude,
        ),
        value=500,
    )


@pytest.mark.parametrize("node_fixture", ["dimmable_light"])
async def test_matter_exception_on_write_attribute(
    menuai: menuai,
    matter_client: MagicMock,
    matter_node: MatterNode,
) -> None:
    """Test if a MatterError gets converted to menuaiError by using a dimmable_light fixture."""
    state = menuai.states.get("number.mock_dimmable_light_on_level")
    assert state
    matter_client.write_attribute.side_effect = MatterError("Boom")
    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            "number",
            "set_value",
            {
                "entity_id": "number.mock_dimmable_light_on_level",
                "value": 500,
            },
            blocking=True,
        )
