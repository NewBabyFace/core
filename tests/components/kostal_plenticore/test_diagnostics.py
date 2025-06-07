"""Test Kostal Plenticore diagnostics."""

from pykoplenti import SettingsData

from menuai.components.diagnostics import REDACTED
from menuai.components.kostal_plenticore.coordinator import Plenticore
from menuai.core import menuai

from tests.common import ANY, MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_entry_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    mock_plenticore: Plenticore,
    init_integration: MockConfigEntry,
) -> None:
    """Test config entry diagnostics."""

    # set some test process and settings data for the diagnostics output
    mock_plenticore.client.get_process_data.return_value = {
        "devices:local": ["HomeGrid_P", "HomePv_P"]
    }

    mock_plenticore.client.get_settings.return_value = {
        "devices:local": [
            SettingsData(
                min="5",
                max="100",
                default=None,
                access="readwrite",
                unit="%",
                id="Battery:MinSoc",
                type="byte",
            )
        ]
    }

    assert await get_diagnostics_for_config_entry(
        menuai, menuai_client, init_integration
    ) == {
        "config_entry": {
            "entry_id": "2ab8dd92a62787ddfe213a67e09406bd",
            "version": 1,
            "minor_version": 1,
            "domain": "kostal_plenticore",
            "title": "scb",
            "data": {"host": "192.168.1.2", "password": REDACTED},
            "options": {},
            "pref_disable_new_entities": False,
            "pref_disable_polling": False,
            "source": "user",
            "unique_id": None,
            "disabled_by": None,
            "created_at": ANY,
            "modified_at": ANY,
            "discovery_keys": {},
            "subentries": [],
        },
        "client": {
            "version": "api_version='0.2.0' hostname='scb' name='PUCK RESTful API' sw_version='01.16.05025'",
            "me": "is_locked=False is_active=True is_authenticated=True permissions=[] is_anonymous=False role='USER'",
            "available_process_data": {"devices:local": ["HomeGrid_P", "HomePv_P"]},
            "available_settings_data": {
                "devices:local": [
                    "min='5' max='100' default=None access='readwrite' unit='%' id='Battery:MinSoc' type='byte'"
                ]
            },
        },
        "device": {
            "configuration_url": "http://192.168.1.2",
            "identifiers": "**REDACTED**",
            "manufacturer": "Kostal",
            "model": "PLENTICORE plus 10",
            "name": "scb",
            "sw_version": "IOC: 01.45 MC: 01.46",
        },
    }
