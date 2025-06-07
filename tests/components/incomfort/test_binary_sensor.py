"""Binary sensor tests for Intergas InComfort integration."""

from unittest.mock import MagicMock, patch

from incomfortclient import FaultCode
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .conftest import MOCK_HEATER_STATUS

from tests.common import snapshot_platform


@patch("menuai.components.incomfort.PLATFORMS", [Platform.BINARY_SENSOR])
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_setup_platform(
    menuai: menuai,
    mock_incomfort: MagicMock,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test the incomfort entities are set up correctly."""
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.parametrize(
    "mock_heater_status",
    [
        MOCK_HEATER_STATUS
        | {
            "is_failed": True,
            "display_code": None,
            "fault_code": FaultCode.CV_TEMPERATURE_TOO_HIGH_E1,
        },
        MOCK_HEATER_STATUS | {"is_pumping": True},
        MOCK_HEATER_STATUS | {"is_burning": True},
        MOCK_HEATER_STATUS | {"is_tapping": True},
    ],
    ids=["is_failed", "is_pumping", "is_burning", "is_tapping"],
)
@patch("menuai.components.incomfort.PLATFORMS", [Platform.BINARY_SENSOR])
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_setup_binary_sensors_alt(
    menuai: menuai,
    mock_incomfort: MagicMock,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test the incomfort heater ."""
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)
