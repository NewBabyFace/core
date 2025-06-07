"""Vera tests."""

from unittest.mock import MagicMock

import pyvera as pv

from menuai.components.light import ATTR_BRIGHTNESS, ATTR_HS_COLOR
from menuai.core import menuai

from .common import ComponentFactory, new_simple_controller_config


async def test_light(
    menuai: menuai, vera_component_factory: ComponentFactory
) -> None:
    """Test function."""
    vera_device: pv.VeraDimmer = MagicMock(spec=pv.VeraDimmer)
    vera_device.device_id = 1
    vera_device.vera_device_id = vera_device.device_id
    vera_device.comm_failure = False
    vera_device.name = "dev1"
    vera_device.category = pv.CATEGORY_DIMMER
    vera_device.is_switched_on = MagicMock(return_value=False)
    vera_device.get_brightness = MagicMock(return_value=0)
    vera_device.get_color = MagicMock(return_value=[0, 0, 0])
    vera_device.is_dimmable = True
    entity_id = "light.dev1_1"

    component_data = await vera_component_factory.configure_component(
        menuai=menuai,
        controller_config=new_simple_controller_config(devices=(vera_device,)),
    )
    update_callback = component_data.controller_data[0].update_callback

    assert menuai.states.get(entity_id).state == "off"

    await menuai.services.async_call(
        "light",
        "turn_on",
        {"entity_id": entity_id},
    )
    await menuai.async_block_till_done()
    vera_device.switch_on.assert_called()
    vera_device.is_switched_on.return_value = True
    update_callback(vera_device)
    await menuai.async_block_till_done()
    assert menuai.states.get(entity_id).state == "on"

    await menuai.services.async_call(
        "light",
        "turn_on",
        {"entity_id": entity_id, ATTR_HS_COLOR: [300, 70]},
    )
    await menuai.async_block_till_done()
    vera_device.set_color.assert_called_with((255, 77, 255))
    vera_device.is_switched_on.return_value = True
    vera_device.get_color.return_value = (255, 77, 255)
    update_callback(vera_device)
    await menuai.async_block_till_done()
    assert menuai.states.get(entity_id).state == "on"
    assert menuai.states.get(entity_id).attributes["hs_color"] == (300.0, 69.804)

    await menuai.services.async_call(
        "light",
        "turn_on",
        {"entity_id": entity_id, ATTR_BRIGHTNESS: 55},
    )
    await menuai.async_block_till_done()
    vera_device.set_brightness.assert_called_with(55)
    vera_device.is_switched_on.return_value = True
    vera_device.get_brightness.return_value = 55
    update_callback(vera_device)
    await menuai.async_block_till_done()
    assert menuai.states.get(entity_id).state == "on"
    assert menuai.states.get(entity_id).attributes["brightness"] == 55

    await menuai.services.async_call(
        "light",
        "turn_off",
        {"entity_id": entity_id},
    )
    await menuai.async_block_till_done()
    vera_device.switch_off.assert_called()
    vera_device.is_switched_on.return_value = False
    update_callback(vera_device)
    await menuai.async_block_till_done()
    assert menuai.states.get(entity_id).state == "off"
