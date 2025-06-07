"""Tests for La Marzocco switches."""

from typing import Any
from unittest.mock import MagicMock, patch

from pylamarzocco.const import SmartStandByType
from pylamarzocco.exceptions import RequestNotSuccessful
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er

from . import WAKE_UP_SLEEP_ENTRY_IDS, async_init_integration

from tests.common import MockConfigEntry, snapshot_platform


async def test_switches(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the La Marzocco switches."""
    with patch("menuai.components.lamarzocco.PLATFORMS", [Platform.SWITCH]):
        await async_init_integration(menuai, mock_config_entry)
    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.parametrize(
    (
        "entity_name",
        "method_name",
        "kwargs",
    ),
    [
        ("", "set_power", {}),
        ("_steam_boiler", "set_steam", {}),
        (
            "_smart_standby_enabled",
            "set_smart_standby",
            {"mode": SmartStandByType.POWER_ON, "minutes": 10},
        ),
    ],
)
async def test_switches_actions(
    menuai: menuai,
    mock_lamarzocco: MagicMock,
    mock_config_entry: MockConfigEntry,
    entity_name: str,
    method_name: str,
    kwargs: dict[str, Any],
) -> None:
    """Test the La Marzocco switches."""
    await async_init_integration(menuai, mock_config_entry)

    serial_number = mock_lamarzocco.serial_number

    control_fn = getattr(mock_lamarzocco, method_name)

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {
            ATTR_ENTITY_ID: f"switch.{serial_number}{entity_name}",
        },
        blocking=True,
    )

    assert len(control_fn.mock_calls) == 1
    control_fn.assert_called_once_with(enabled=False, **kwargs)

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: f"switch.{serial_number}{entity_name}",
        },
        blocking=True,
    )

    assert len(control_fn.mock_calls) == 2
    control_fn.assert_called_with(enabled=True, **kwargs)


async def test_auto_on_off_switches(
    menuai: menuai,
    mock_lamarzocco: MagicMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the auto on off/switches."""

    await async_init_integration(menuai, mock_config_entry)

    serial_number = mock_lamarzocco.serial_number

    for wake_up_sleep_entry_id in WAKE_UP_SLEEP_ENTRY_IDS:
        state = menuai.states.get(
            f"switch.{serial_number}_auto_on_off_{wake_up_sleep_entry_id}"
        )
        assert state
        assert state == snapshot(name=f"state.auto_on_off_{wake_up_sleep_entry_id}")

        entry = entity_registry.async_get(state.entity_id)
        assert entry
        assert entry == snapshot(name=f"entry.auto_on_off_{wake_up_sleep_entry_id}")

        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {
                ATTR_ENTITY_ID: f"switch.{serial_number}_auto_on_off_{wake_up_sleep_entry_id}",
            },
            blocking=True,
        )

        wake_up_sleep_entry = (
            mock_lamarzocco.schedule.smart_wake_up_sleep.schedules_dict[
                wake_up_sleep_entry_id
            ]
        )
        assert wake_up_sleep_entry
        wake_up_sleep_entry.enabled = False

        mock_lamarzocco.set_wakeup_schedule.assert_called_with(wake_up_sleep_entry)

        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {
                ATTR_ENTITY_ID: f"switch.{serial_number}_auto_on_off_{wake_up_sleep_entry_id}",
            },
            blocking=True,
        )
        wake_up_sleep_entry.enabled = True
        mock_lamarzocco.set_wakeup_schedule.assert_called_with(wake_up_sleep_entry)


async def test_switch_exceptions(
    menuai: menuai,
    mock_lamarzocco: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the La Marzocco switches."""
    await async_init_integration(menuai, mock_config_entry)

    serial_number = mock_lamarzocco.serial_number

    state = menuai.states.get(f"switch.{serial_number}")
    assert state

    mock_lamarzocco.set_power.side_effect = RequestNotSuccessful("Boom")

    with pytest.raises(menuaiError) as exc_info:
        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {
                ATTR_ENTITY_ID: f"switch.{serial_number}",
            },
            blocking=True,
        )
    assert exc_info.value.translation_key == "switch_off_error"

    with pytest.raises(menuaiError) as exc_info:
        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {
                ATTR_ENTITY_ID: f"switch.{serial_number}",
            },
            blocking=True,
        )
    assert exc_info.value.translation_key == "switch_on_error"

    state = menuai.states.get(f"switch.{serial_number}_auto_on_off_os2oswx")
    assert state

    mock_lamarzocco.set_wakeup_schedule.side_effect = RequestNotSuccessful("Boom")
    with pytest.raises(menuaiError) as exc_info:
        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {
                ATTR_ENTITY_ID: f"switch.{serial_number}_auto_on_off_os2oswx",
            },
            blocking=True,
        )
    assert exc_info.value.translation_key == "auto_on_off_error"
