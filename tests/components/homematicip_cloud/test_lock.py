"""Tests for HomematicIP Cloud locks."""

from unittest.mock import patch

from homematicip.base.enums import LockState as HomematicLockState, MotorState
import pytest

from menuai.components.lock import LockEntityFeature, LockState
from menuai.const import ATTR_SUPPORTED_FEATURES
from menuai.core import menuai
from menuai.exceptions import menuaiError

from .helper import HomeFactory, async_manipulate_test_data, get_and_check_entity_basics


async def test_hmip_doorlockdrive(
    menuai: menuai, default_mock_hap_factory: HomeFactory
) -> None:
    """Test HomematicipDoorLockDrive."""
    entity_id = "lock.haustuer"
    entity_name = "Haustuer"
    device_model = "HmIP-DLD"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=[entity_name]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        menuai, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.attributes[ATTR_SUPPORTED_FEATURES] == LockEntityFeature.OPEN

    await menuai.services.async_call(
        "lock",
        "open",
        {"entity_id": entity_id},
        blocking=True,
    )
    assert hmip_device.mock_calls[-1][0] == "set_lock_state_async"
    assert hmip_device.mock_calls[-1][1] == (HomematicLockState.OPEN,)

    await menuai.services.async_call(
        "lock",
        "lock",
        {"entity_id": entity_id},
        blocking=True,
    )
    assert hmip_device.mock_calls[-1][0] == "set_lock_state_async"
    assert hmip_device.mock_calls[-1][1] == (HomematicLockState.LOCKED,)

    await menuai.services.async_call(
        "lock",
        "unlock",
        {"entity_id": entity_id},
        blocking=True,
    )

    assert hmip_device.mock_calls[-1][0] == "set_lock_state_async"
    assert hmip_device.mock_calls[-1][1] == (HomematicLockState.UNLOCKED,)

    await async_manipulate_test_data(
        menuai, hmip_device, "motorState", MotorState.CLOSING
    )
    ha_state = menuai.states.get(entity_id)
    assert ha_state.state == LockState.LOCKING

    await async_manipulate_test_data(
        menuai, hmip_device, "motorState", MotorState.OPENING
    )
    ha_state = menuai.states.get(entity_id)
    assert ha_state.state == LockState.UNLOCKING


async def test_hmip_doorlockdrive_handle_errors(
    menuai: menuai, default_mock_hap_factory: HomeFactory
) -> None:
    """Test HomematicipDoorLockDrive."""
    entity_id = "lock.haustuer"
    entity_name = "Haustuer"
    device_model = "HmIP-DLD"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=[entity_name]
    )
    with patch(
        "homematicip.device.DoorLockDrive.set_lock_state_async",
        return_value={
            "errorCode": "INVALID_NUMBER_PARAMETER_VALUE",
            "minValue": 0.0,
            "maxValue": 1.01,
        },
    ):
        get_and_check_entity_basics(
            menuai, mock_hap, entity_id, entity_name, device_model
        )

        with pytest.raises(menuaiError):
            await menuai.services.async_call(
                "lock",
                "open",
                {"entity_id": entity_id},
                blocking=True,
            )

        with pytest.raises(menuaiError):
            await menuai.services.async_call(
                "lock",
                "lock",
                {"entity_id": entity_id},
                blocking=True,
            )

        with pytest.raises(menuaiError):
            await menuai.services.async_call(
                "lock",
                "unlock",
                {"entity_id": entity_id},
                blocking=True,
            )
