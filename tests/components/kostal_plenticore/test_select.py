"""Test the Kostal Plenticore Solar Inverter select platform."""

from pykoplenti import SettingsData

from menuai.components.kostal_plenticore.coordinator import Plenticore
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry


async def test_select_battery_charging_usage_available(
    menuai: menuai,
    mock_plenticore: Plenticore,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test that the battery charging usage select entity is added if the settings are available."""

    mock_plenticore.client.get_settings.return_value = {
        "devices:local": [
            SettingsData(
                min=None,
                max=None,
                default=None,
                access="readwrite",
                unit=None,
                id="Battery:SmartBatteryControl:Enable",
                type="string",
            ),
            SettingsData(
                min=None,
                max=None,
                default=None,
                access="readwrite",
                unit=None,
                id="Battery:TimeControl:Enable",
                type="string",
            ),
        ]
    }

    mock_config_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert entity_registry.async_is_registered("select.battery_charging_usage_mode")


async def test_select_battery_charging_usage_not_available(
    menuai: menuai,
    mock_plenticore: Plenticore,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test that the battery charging usage select entity is not added if the settings are unavailable."""

    mock_config_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert not entity_registry.async_is_registered("select.battery_charging_usage_mode")
