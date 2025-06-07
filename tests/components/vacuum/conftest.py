"""Fixtures for Vacuum platform tests."""

from collections.abc import AsyncGenerator, Generator
from unittest.mock import MagicMock, patch

import pytest

from menuai.components.vacuum import DOMAIN, VacuumEntityFeature
from menuai.config_entries import ConfigEntry, ConfigFlow
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er, frame
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import MockVacuum

from tests.common import (
    MockConfigEntry,
    MockModule,
    MockPlatform,
    mock_config_flow,
    mock_integration,
    mock_platform,
)

TEST_DOMAIN = "test"


class MockFlow(ConfigFlow):
    """Test flow."""


@pytest.fixture
def config_flow_fixture(menuai: menuai) -> Generator[None]:
    """Mock config flow."""
    mock_platform(menuai, f"{TEST_DOMAIN}.config_flow")

    with mock_config_flow(TEST_DOMAIN, MockFlow):
        yield


@pytest.fixture(name="supported_features")
async def vacuum_supported_features() -> VacuumEntityFeature:
    """Return the supported features for the test vacuum entity."""
    return (
        VacuumEntityFeature.PAUSE
        | VacuumEntityFeature.STOP
        | VacuumEntityFeature.RETURN_HOME
        | VacuumEntityFeature.FAN_SPEED
        | VacuumEntityFeature.BATTERY
        | VacuumEntityFeature.CLEAN_SPOT
        | VacuumEntityFeature.MAP
        | VacuumEntityFeature.STATE
        | VacuumEntityFeature.START
    )


@pytest.fixture(name="mock_vacuum_entity")
async def setup_vacuum_platform_test_entity(
    menuai: menuai,
    config_flow_fixture: None,
    entity_registry: er.EntityRegistry,
    supported_features: VacuumEntityFeature,
) -> MagicMock:
    """Set up vacuum entity using an entity platform."""

    async def async_setup_entry_init(
        menuai: menuai, config_entry: ConfigEntry
    ) -> bool:
        """Set up test config entry."""
        await menuai.config_entries.async_forward_entry_setups(
            config_entry, [Platform.VACUUM]
        )
        return True

    mock_integration(
        menuai,
        MockModule(
            TEST_DOMAIN,
            async_setup_entry=async_setup_entry_init,
        ),
    )

    entity = MockVacuum(
        supported_features=supported_features,
    )

    async def async_setup_entry_platform(
        menuai: menuai,
        config_entry: ConfigEntry,
        async_add_entities: AddConfigEntryEntitiesCallback,
    ) -> None:
        """Set up test vacuum platform via config entry."""
        async_add_entities([entity])

    mock_platform(
        menuai,
        f"{TEST_DOMAIN}.{DOMAIN}",
        MockPlatform(async_setup_entry=async_setup_entry_platform),
    )

    config_entry = MockConfigEntry(domain=TEST_DOMAIN)
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    state = menuai.states.get(entity.entity_id)
    assert state is not None

    return entity


@pytest.fixture(name="mock_as_custom_component")
async def mock_frame(menuai: menuai) -> AsyncGenerator[None]:
    """Mock frame."""
    with patch(
        "menuai.helpers.frame.get_integration_frame",
        return_value=frame.IntegrationFrame(
            custom_integration=True,
            integration="alarm_control_panel",
            module="test_init.py",
            relative_filename="test_init.py",
            frame=frame.get_current_frame(),
        ),
    ):
        yield
