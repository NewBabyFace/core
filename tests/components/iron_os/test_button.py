"""Tests for the IronOS button platform."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

from pynecil import CharSetting, CommunicationError
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from menuai.config_entries import ConfigEntryState
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.exceptions import ServiceValidationError
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry, snapshot_platform


@pytest.fixture(autouse=True)
async def button_only() -> AsyncGenerator[None]:
    """Enable only the button platform."""
    with patch(
        "menuai.components.iron_os.PLATFORMS",
        [Platform.BUTTON],
    ):
        yield


@pytest.mark.usefixtures(
    "entity_registry_enabled_by_default", "mock_pynecil", "ble_device"
)
async def test_button_platform(
    menuai: menuai,
    config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test the IronOS button platform."""
    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    await snapshot_platform(menuai, entity_registry, snapshot, config_entry.entry_id)


@pytest.mark.parametrize(
    ("entity_id", "call_args"),
    [
        ("button.pinecil_save_settings", (CharSetting.SETTINGS_SAVE, True)),
        ("button.pinecil_restore_default_settings", (CharSetting.SETTINGS_RESET, True)),
    ],
)
@pytest.mark.usefixtures("entity_registry_enabled_by_default", "ble_device")
async def test_button_press(
    menuai: menuai,
    config_entry: MockConfigEntry,
    mock_pynecil: AsyncMock,
    entity_id: str,
    call_args: tuple[tuple[CharSetting, bool]],
) -> None:
    """Test button press method."""

    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    await menuai.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    mock_pynecil.write.assert_called_once_with(*call_args)


@pytest.mark.usefixtures("entity_registry_enabled_by_default", "ble_device")
async def test_button_press_exception(
    menuai: menuai,
    config_entry: MockConfigEntry,
    mock_pynecil: AsyncMock,
) -> None:
    """Test button press method."""

    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    mock_pynecil.write.side_effect = CommunicationError

    with pytest.raises(
        ServiceValidationError,
        match="Failed to submit setting to device, try again later",
    ):
        await menuai.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: "button.pinecil_save_settings"},
            blocking=True,
        )
