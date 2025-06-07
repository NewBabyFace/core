"""Tests for the plaato binary sensors."""

from unittest.mock import patch

from pyplaato.models.device import PlaatoDeviceType
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import init_integration

from tests.common import snapshot_platform


# note: PlaatoDeviceType.Airlock does not provide binary sensors
@pytest.mark.parametrize("device_type", [PlaatoDeviceType.Keg])
async def test_binary_sensors(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    device_type: PlaatoDeviceType,
) -> None:
    """Test binary sensors."""
    with patch(
        "menuai.components.plaato.PLATFORMS",
        [Platform.BINARY_SENSOR],
    ):
        entry = await init_integration(menuai, device_type)

    await snapshot_platform(menuai, entity_registry, snapshot, entry.entry_id)
