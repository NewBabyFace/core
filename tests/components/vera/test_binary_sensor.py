"""Vera tests."""

from unittest.mock import MagicMock

import pyvera as pv

from menuai.core import menuai

from .common import ComponentFactory, new_simple_controller_config


async def test_binary_sensor(
    menuai: menuai, vera_component_factory: ComponentFactory
) -> None:
    """Test function."""
    vera_device: pv.VeraBinarySensor = MagicMock(spec=pv.VeraBinarySensor)
    vera_device.device_id = 1
    vera_device.comm_failure = False
    vera_device.vera_device_id = vera_device.device_id
    vera_device.name = "dev1"
    vera_device.is_tripped = False
    entity_id = "binary_sensor.dev1_1"

    component_data = await vera_component_factory.configure_component(
        menuai=menuai,
        controller_config=new_simple_controller_config(devices=(vera_device,)),
    )
    update_callback = component_data.controller_data[0].update_callback

    vera_device.is_tripped = False
    update_callback(vera_device)
    await menuai.async_block_till_done()
    assert menuai.states.get(entity_id).state == "off"

    vera_device.is_tripped = True
    update_callback(vera_device)
    await menuai.async_block_till_done()
    assert menuai.states.get(entity_id).state == "on"
