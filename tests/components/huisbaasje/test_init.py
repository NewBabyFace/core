"""Test cases for the initialisation of the Huisbaasje integration."""

from unittest.mock import patch

from energyflip import EnergyFlipException

from menuai.components.huisbaasje.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_ID, CONF_PASSWORD, CONF_USERNAME, STATE_UNAVAILABLE
from menuai.core import menuai

from .test_data import MOCK_CURRENT_MEASUREMENTS

from tests.common import MockConfigEntry


async def test_setup_entry(menuai: menuai) -> None:
    """Test for successfully setting a config entry."""
    with (
        patch(
            "energyflip.EnergyFlip.authenticate", return_value=None
        ) as mock_authenticate,
        patch(
            "energyflip.EnergyFlip.is_authenticated", return_value=True
        ) as mock_is_authenticated,
        patch(
            "energyflip.EnergyFlip.current_measurements",
            return_value=MOCK_CURRENT_MEASUREMENTS,
        ) as mock_current_measurements,
    ):
        config_entry = MockConfigEntry(
            version=1,
            domain=DOMAIN,
            title="userId",
            data={
                CONF_ID: "userId",
                CONF_USERNAME: "username",
                CONF_PASSWORD: "password",
            },
            source="test",
        )
        config_entry.add_to_menuai(menuai)

        assert config_entry.state is ConfigEntryState.NOT_LOADED
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

        # Assert integration is loaded
        assert config_entry.state is ConfigEntryState.LOADED

        # Assert entities are loaded
        entities = menuai.states.async_entity_ids("sensor")
        assert len(entities) == 18

        # Assert mocks are called
        assert len(mock_authenticate.mock_calls) == 1
        assert len(mock_is_authenticated.mock_calls) == 1
        assert len(mock_current_measurements.mock_calls) == 1


async def test_setup_entry_error(menuai: menuai) -> None:
    """Test for successfully setting a config entry."""
    with patch(
        "energyflip.EnergyFlip.authenticate", side_effect=EnergyFlipException
    ) as mock_authenticate:
        config_entry = MockConfigEntry(
            version=1,
            domain=DOMAIN,
            title="userId",
            data={
                CONF_ID: "userId",
                CONF_USERNAME: "username",
                CONF_PASSWORD: "password",
            },
            source="test",
        )
        config_entry.add_to_menuai(menuai)

        assert config_entry.state is ConfigEntryState.NOT_LOADED
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

        # Assert integration is loaded with error
        assert config_entry.state is ConfigEntryState.SETUP_ERROR
        assert DOMAIN not in menuai.data

        # Assert entities are not loaded
        entities = menuai.states.async_entity_ids("sensor")
        assert len(entities) == 0

        # Assert mocks are called
        assert len(mock_authenticate.mock_calls) == 1


async def test_unload_entry(menuai: menuai) -> None:
    """Test for successfully unloading the config entry."""
    with (
        patch(
            "energyflip.EnergyFlip.authenticate", return_value=None
        ) as mock_authenticate,
        patch(
            "energyflip.EnergyFlip.is_authenticated", return_value=True
        ) as mock_is_authenticated,
        patch(
            "energyflip.EnergyFlip.current_measurements",
            return_value=MOCK_CURRENT_MEASUREMENTS,
        ) as mock_current_measurements,
    ):
        config_entry = MockConfigEntry(
            version=1,
            domain=DOMAIN,
            title="userId",
            data={
                CONF_ID: "userId",
                CONF_USERNAME: "username",
                CONF_PASSWORD: "password",
            },
            source="test",
        )
        config_entry.add_to_menuai(menuai)

        # Load config entry
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()
        assert config_entry.state is ConfigEntryState.LOADED
        entities = menuai.states.async_entity_ids("sensor")
        assert len(entities) == 18

        # Unload config entry
        await menuai.config_entries.async_unload(config_entry.entry_id)
        assert config_entry.state is ConfigEntryState.NOT_LOADED
        entities = menuai.states.async_entity_ids("sensor")
        assert len(entities) == 18
        for entity in entities:
            assert menuai.states.get(entity).state == STATE_UNAVAILABLE

        # Remove config entry
        await menuai.config_entries.async_remove(config_entry.entry_id)
        await menuai.async_block_till_done()
        entities = menuai.states.async_entity_ids("sensor")
        assert len(entities) == 0

        # Assert mocks are called
        assert len(mock_authenticate.mock_calls) == 1
        assert len(mock_is_authenticated.mock_calls) == 1
        assert len(mock_current_measurements.mock_calls) == 1
