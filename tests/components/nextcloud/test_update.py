"""Tests for the Nextcloud update entity."""

from copy import deepcopy
from unittest.mock import patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.const import STATE_OFF, STATE_ON, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import init_integration
from .const import NC_DATA, VALID_CONFIG

from tests.common import snapshot_platform


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_async_setup_entry(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test a successful setup entry."""
    with patch("menuai.components.nextcloud.PLATFORMS", [Platform.UPDATE]):
        entry = await init_integration(menuai, VALID_CONFIG, NC_DATA)

    await snapshot_platform(menuai, entity_registry, snapshot, entry.entry_id)


async def test_setup_entity_without_update(
    menuai: menuai, snapshot: SnapshotAssertion
) -> None:
    """Test update entity is created w/o available update."""
    with patch("menuai.components.nextcloud.PLATFORMS", [Platform.UPDATE]):
        await init_integration(menuai, VALID_CONFIG, NC_DATA)

    states = menuai.states.async_all()
    assert len(states) == 1
    assert states[0].state == STATE_OFF
    assert states[0].attributes["installed_version"] == "28.0.4.1"
    assert states[0].attributes["latest_version"] == "28.0.4.1"
    assert (
        states[0].attributes["release_url"] == "https://nextcloud.com/changelog/#28-0-4"
    )


async def test_setup_entity_with_update(
    menuai: menuai, snapshot: SnapshotAssertion
) -> None:
    """Test update entity is created with available update."""
    data = deepcopy(NC_DATA)
    data["nextcloud"]["system"]["update"]["available"] = True
    data["nextcloud"]["system"]["update"]["available_version"] = "30.0.0.0"
    with patch("menuai.components.nextcloud.PLATFORMS", [Platform.UPDATE]):
        await init_integration(menuai, VALID_CONFIG, data)

    states = menuai.states.async_all()
    assert len(states) == 1
    assert states[0].state == STATE_ON
    assert states[0].attributes["installed_version"] == "28.0.4.1"
    assert states[0].attributes["latest_version"] == "30.0.0.0"
    assert (
        states[0].attributes["release_url"] == "https://nextcloud.com/changelog/#30-0-0"
    )


async def test_setup_no_entity(menuai: menuai) -> None:
    """Test no update entity is created, when no data available."""
    data = deepcopy(NC_DATA)
    data["nextcloud"]["system"].pop("update")  # only nc<28.0.0
    with patch("menuai.components.nextcloud.PLATFORMS", [Platform.UPDATE]):
        await init_integration(menuai, VALID_CONFIG, data)

    states = menuai.states.async_all()
    assert len(states) == 0
