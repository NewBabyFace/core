"""Test the OctoPrint services."""

from unittest.mock import patch

from menuai.components.octoprint.const import (
    CONF_BAUDRATE,
    DOMAIN,
    SERVICE_CONNECT,
)
from menuai.const import ATTR_DEVICE_ID, CONF_PORT, CONF_PROFILE_NAME
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from . import init_integration


async def test_connect_default(
    menuai: menuai, device_registry: dr.DeviceRegistry
) -> None:
    """Test the connect to printer service."""
    await init_integration(menuai, "sensor")

    device = dr.async_entries_for_config_entry(device_registry, "uuid")[0]

    # Test pausing the printer when it is printing
    with patch("pyoctoprintapi.OctoprintClient.connect") as connect_command:
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_CONNECT,
            {
                ATTR_DEVICE_ID: device.id,
            },
            blocking=True,
        )

        assert len(connect_command.mock_calls) == 1
        connect_command.assert_called_with(
            port=None, printer_profile=None, baud_rate=None
        )


async def test_connect_all_arguments(
    menuai: menuai, device_registry: dr.DeviceRegistry
) -> None:
    """Test the connect to printer service."""
    await init_integration(menuai, "sensor")

    device = dr.async_entries_for_config_entry(device_registry, "uuid")[0]

    # Test pausing the printer when it is printing
    with patch("pyoctoprintapi.OctoprintClient.connect") as connect_command:
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_CONNECT,
            {
                ATTR_DEVICE_ID: device.id,
                CONF_PROFILE_NAME: "Test Profile",
                CONF_PORT: "VIRTUAL",
                CONF_BAUDRATE: 9600,
            },
            blocking=True,
        )

        assert len(connect_command.mock_calls) == 1
        connect_command.assert_called_with(
            port="VIRTUAL", printer_profile="Test Profile", baud_rate=9600
        )
