"""Test BMW binary sensors."""

from unittest.mock import patch

from freezegun import freeze_time
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_mocked_integration

from tests.common import snapshot_platform


@freeze_time("2023-06-22 10:30:00+00:00")
@pytest.mark.usefixtures("bmw_fixture")
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_entity_state_attrs(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test binary sensor states and attributes."""

    # Setup component
    with patch(
        "menuai.components.bmw_connected_drive.PLATFORMS",
        [Platform.BINARY_SENSOR],
    ):
        mock_config_entry = await setup_mocked_integration(menuai)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)
