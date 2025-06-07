"""Tests for the Flick Electric integration."""

from pyflick.types import FlickPrice

from menuai.components.flick_electric.const import (
    CONF_ACCOUNT_ID,
    CONF_SUPPLY_NODE_REF,
)
from menuai.const import CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai

from tests.common import MockConfigEntry

CONF = {
    CONF_USERNAME: "9973debf-963f-49b0-9a73-ba9c3400cbed@anonymised.example.com",
    CONF_PASSWORD: "test-password",
    CONF_ACCOUNT_ID: "134800",
    CONF_SUPPLY_NODE_REF: "/network/nz/supply_nodes/ed7617df-4b10-4c8a-a05d-deadbeef8299",
}


async def setup_integration(menuai: menuai, config_entry: MockConfigEntry) -> None:
    """Fixture for setting up the component."""
    config_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()


def _mock_flick_price():
    return FlickPrice(
        {
            "cost": "0.25",
            "quantity": "1.0",
            "status": "final",
            "start_at": "2024-01-01T00:00:00Z",
            "end_at": "2024-01-01T00:00:00Z",
            "type": "flat",
            "components": [
                {
                    "charge_method": "kwh",
                    "charge_setter": "network",
                    "value": "1.00",
                    "single_unit_price": "1.00",
                    "quantity": "1.0",
                    "unit_code": "NZD",
                    "charge_per": "kwh",
                    "flow_direction": "import",
                },
                {
                    "charge_method": "kwh",
                    "charge_setter": "nonsupported",
                    "value": "1.00",
                    "single_unit_price": "1.00",
                    "quantity": "1.0",
                    "unit_code": "NZD",
                    "charge_per": "kwh",
                    "flow_direction": "import",
                },
            ],
        }
    )
