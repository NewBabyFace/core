"""Test Enphase Envoy diagnostics."""

from unittest.mock import AsyncMock

from freezegun.api import FrozenDateTimeFactory
from pyenphase.exceptions import EnvoyError
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.enphase_envoy.const import (
    DOMAIN,
    OPTION_DIAGNOSTICS_INCLUDE_FIXTURES,
)
from menuai.components.enphase_envoy.coordinator import MAC_VERIFICATION_DELAY
from menuai.core import menuai

from . import setup_integration

from tests.common import MockConfigEntry, async_fire_time_changed
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator

# Fields to exclude from snapshot as they change each run
TO_EXCLUDE = {
    "id",
    "device_id",
    "via_device_id",
    "last_updated",
    "last_changed",
    "last_reported",
    "created_at",
    "modified_at",
}


def limit_diagnostic_attrs(prop, path) -> bool:
    """Mark attributes to exclude from diagnostic snapshot."""
    return prop in TO_EXCLUDE


async def test_entry_diagnostics(
    menuai: menuai,
    config_entry: MockConfigEntry,
    menuai_client: ClientSessionGenerator,
    mock_envoy: AsyncMock,
    snapshot: SnapshotAssertion,
) -> None:
    """Test config entry diagnostics."""
    await setup_integration(menuai, config_entry)
    assert await get_diagnostics_for_config_entry(
        menuai, menuai_client, config_entry
    ) == snapshot(exclude=limit_diagnostic_attrs)


@pytest.fixture(name="config_entry_options")
def config_entry_options_fixture(menuai: menuai, config: dict[str, str]):
    """Define a config entry fixture."""
    return MockConfigEntry(
        domain=DOMAIN,
        entry_id="45a36e55aaddb2007c5f6602e0c38e72",
        title="Envoy 1234",
        unique_id="1234",
        data=config,
        options={OPTION_DIAGNOSTICS_INCLUDE_FIXTURES: True},
    )


async def test_entry_diagnostics_with_fixtures(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    config_entry_options: MockConfigEntry,
    mock_envoy: AsyncMock,
    snapshot: SnapshotAssertion,
) -> None:
    """Test config entry diagnostics."""
    await setup_integration(menuai, config_entry_options)
    assert await get_diagnostics_for_config_entry(
        menuai, menuai_client, config_entry_options
    ) == snapshot(exclude=limit_diagnostic_attrs)


async def test_entry_diagnostics_with_fixtures_with_error(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    config_entry_options: MockConfigEntry,
    snapshot: SnapshotAssertion,
    mock_envoy: AsyncMock,
) -> None:
    """Test config entry diagnostics."""
    await setup_integration(menuai, config_entry_options)
    mock_envoy.request.side_effect = EnvoyError("Test")
    assert await get_diagnostics_for_config_entry(
        menuai, menuai_client, config_entry_options
    ) == snapshot(exclude=limit_diagnostic_attrs)


async def test_entry_diagnostics_with_interface_information(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    mock_envoy: AsyncMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test config entry diagnostics including interface data."""
    await setup_integration(menuai, config_entry)

    # move time forward so interface information is collected
    freezer.tick(MAC_VERIFICATION_DELAY)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert await get_diagnostics_for_config_entry(
        menuai, menuai_client, config_entry
    ) == snapshot(exclude=limit_diagnostic_attrs)
