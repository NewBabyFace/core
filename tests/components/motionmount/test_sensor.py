"""Tests for the MotionMount Sensor platform."""

from unittest.mock import patch

from motionmount import MotionMountSystemError
import pytest

from menuai.core import menuai

from . import MAC, ZEROCONF_NAME

from tests.common import MockConfigEntry


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
@pytest.mark.parametrize(
    ("system_status", "state"),
    [
        (None, "none"),
        (MotionMountSystemError.MotorError, "motor"),
        (MotionMountSystemError.ObstructionDetected, "obstruction"),
        (MotionMountSystemError.TVWidthConstraintError, "tv_width_constraint"),
        (MotionMountSystemError.HDMICECError, "hdmi_cec"),
        (MotionMountSystemError.InternalError, "internal"),
    ],
)
async def test_error_status_sensor_states(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    system_status: MotionMountSystemError,
    state: str,
) -> None:
    """Tests the state attributes."""
    with patch(
        "menuai.components.motionmount.motionmount.MotionMount",
        autospec=True,
    ) as motionmount_mock:
        motionmount_mock.return_value.name = ZEROCONF_NAME
        motionmount_mock.return_value.mac = MAC
        motionmount_mock.return_value.is_authenticated = True
        motionmount_mock.return_value.system_status = [system_status]

        mock_config_entry.add_to_menuai(menuai)

        assert await menuai.config_entries.async_setup(mock_config_entry.entry_id)

        assert menuai.states.get("sensor.my_motionmount_error_status").state == state
