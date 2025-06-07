"""Vera tests."""

from unittest.mock import MagicMock

import pyvera as pv

from menuai.components.lock import LockState
from menuai.core import menuai

from .common import ComponentFactory, new_simple_controller_config


async def test_lock(
    menuai: menuai, vera_component_factory: ComponentFactory
) -> None:
    """Test function."""
    vera_device: pv.VeraLock = MagicMock(spec=pv.VeraLock)
    vera_device.device_id = 1
    vera_device.vera_device_id = vera_device.device_id
    vera_device.comm_failure = False
    vera_device.name = "dev1"
    vera_device.category = pv.CATEGORY_LOCK
    vera_device.is_locked = MagicMock(return_value=False)
    entity_id = "lock.dev1_1"

    component_data = await vera_component_factory.configure_component(
        menuai=menuai,
        controller_config=new_simple_controller_config(devices=(vera_device,)),
    )
    update_callback = component_data.controller_data[0].update_callback

    assert menuai.states.get(entity_id).state == LockState.UNLOCKED

    await menuai.services.async_call(
        "lock",
        "lock",
        {"entity_id": entity_id},
    )
    await menuai.async_block_till_done()
    vera_device.lock.assert_called()
    vera_device.is_locked.return_value = True
    update_callback(vera_device)
    await menuai.async_block_till_done()
    assert menuai.states.get(entity_id).state == LockState.LOCKED

    await menuai.services.async_call(
        "lock",
        "unlock",
        {"entity_id": entity_id},
    )
    await menuai.async_block_till_done()
    vera_device.unlock.assert_called()
    vera_device.is_locked.return_value = False
    update_callback(vera_device)
    await menuai.async_block_till_done()
    assert menuai.states.get(entity_id).state == LockState.UNLOCKED
