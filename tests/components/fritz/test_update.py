"""Tests for Fritz!Tools update platform."""

from unittest.mock import patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.fritz.const import DOMAIN
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .const import (
    MOCK_FB_SERVICES,
    MOCK_FIRMWARE_AVAILABLE,
    MOCK_FIRMWARE_RELEASE_URL,
    MOCK_USER_DATA,
)

from tests.common import MockConfigEntry, snapshot_platform

AVAILABLE_UPDATE = {
    "UserInterface1": {
        "GetInfo": {
            "NewX_AVM-DE_Version": MOCK_FIRMWARE_AVAILABLE,
            "NewX_AVM-DE_InfoURL": MOCK_FIRMWARE_RELEASE_URL,
        },
    }
}


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_update_entities_initialized(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    fc_class_mock,
    fh_class_mock,
    snapshot: SnapshotAssertion,
) -> None:
    """Test update entities."""

    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_DATA)
    entry.add_to_menuai(menuai)

    with patch("menuai.components.fritz.PLATFORMS", [Platform.UPDATE]):
        assert await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    await snapshot_platform(menuai, entity_registry, snapshot, entry.entry_id)


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_update_available(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    fc_class_mock,
    fh_class_mock,
    snapshot: SnapshotAssertion,
) -> None:
    """Test update entities."""

    fc_class_mock().override_services({**MOCK_FB_SERVICES, **AVAILABLE_UPDATE})

    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_DATA)
    entry.add_to_menuai(menuai)

    with patch("menuai.components.fritz.PLATFORMS", [Platform.UPDATE]):
        assert await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    await snapshot_platform(menuai, entity_registry, snapshot, entry.entry_id)


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_available_update_can_be_installed(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    fc_class_mock,
    fh_class_mock,
    snapshot: SnapshotAssertion,
) -> None:
    """Test update entities."""

    fc_class_mock().override_services({**MOCK_FB_SERVICES, **AVAILABLE_UPDATE})

    with (
        patch(
            "menuai.components.fritz.coordinator.FritzBoxTools.async_trigger_firmware_update",
            return_value=True,
        ) as mocked_update_call,
        patch("menuai.components.fritz.PLATFORMS", [Platform.UPDATE]),
    ):
        entry = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_DATA)
        entry.add_to_menuai(menuai)

        assert await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

        await snapshot_platform(menuai, entity_registry, snapshot, entry.entry_id)

        await menuai.services.async_call(
            "update",
            "install",
            {"entity_id": "update.mock_title_fritz_os"},
            blocking=True,
        )
        mocked_update_call.assert_called_once()
