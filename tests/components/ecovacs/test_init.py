"""Test init of ecovacs."""

from unittest.mock import Mock, patch

from deebot_client.exceptions import DeebotError, InvalidAuthenticationError
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.ecovacs.const import DOMAIN
from menuai.components.ecovacs.controller import EcovacsController
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from tests.common import MockConfigEntry


@pytest.mark.usefixtures(
    "mock_authenticator", "mock_mqtt_client", "mock_device_execute"
)
async def test_load_unload_config_entry(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test loading and unloading the integration."""
    with patch(
        "menuai.components.ecovacs.EcovacsController",
        autospec=True,
    ):
        mock_config_entry.add_to_menuai(menuai)

        await menuai.config_entries.async_setup(mock_config_entry.entry_id)
        await menuai.async_block_till_done()

        assert mock_config_entry.state is ConfigEntryState.LOADED
        assert DOMAIN not in menuai.data
        controller = mock_config_entry.runtime_data
        assert isinstance(controller, EcovacsController)
        controller.initialize.assert_called_once()

        await menuai.config_entries.async_unload(mock_config_entry.entry_id)
        await menuai.async_block_till_done()
        controller.teardown.assert_called_once()

        assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


@pytest.fixture
def mock_api_client(mock_authenticator: Mock) -> Mock:
    """Mock the API client."""
    with patch(
        "menuai.components.ecovacs.controller.ApiClient",
        autospec=True,
    ) as mock_api_client:
        yield mock_api_client.return_value


async def test_config_entry_not_ready(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_api_client: Mock,
) -> None:
    """Test the Ecovacs configuration entry not ready."""
    mock_api_client.get_devices.side_effect = DeebotError

    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_invalid_auth(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_api_client: Mock,
) -> None:
    """Test auth error during setup."""
    mock_api_client.get_devices.side_effect = InvalidAuthenticationError
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR


async def test_devices_in_dr(
    device_registry: dr.DeviceRegistry,
    controller: EcovacsController,
    snapshot: SnapshotAssertion,
) -> None:
    """Test all devices are in the device registry."""
    for device in controller.devices:
        assert (
            device_entry := device_registry.async_get_device(
                identifiers={(DOMAIN, device.device_info["did"])}
            )
        )
        assert device_entry == snapshot(name=device.device_info["did"])


@pytest.mark.usefixtures(
    "entity_registry_enabled_by_default", "mock_vacbot", "init_integration"
)
@pytest.mark.parametrize(
    ("device_fixture", "entities"),
    [
        ("yna5x1", 26),
        ("5xu9h3", 25),
        ("123", 1),
    ],
)
async def test_all_entities_loaded(
    menuai: menuai,
    device_fixture: str,
    entities: int,
) -> None:
    """Test that all entities are loaded together."""
    assert menuai.states.async_entity_ids_count() == entities, (
        f"loaded entities for {device_fixture}: {menuai.states.async_entity_ids()}"
    )
