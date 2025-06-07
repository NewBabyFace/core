"""Fixtures for command_line."""

from typing import Any

import pytest

from menuai import setup
from menuai.components.command_line.const import DOMAIN
from menuai.core import menuai


@pytest.fixture(name="get_config")
async def get_config_to_integration_load() -> dict[str, Any]:
    """Return default minimal configuration.

    To override the config, tests can be marked with:
    @pytest.mark.parametrize("get_config", [{...}])
    """

    return {
        "command_line": [
            {
                "binary_sensor": {
                    "name": "Test",
                    "command": "echo 1",
                    "payload_on": "1",
                    "payload_off": "0",
                    "command_timeout": 15,
                }
            },
            {
                "cover": {
                    "name": "Test",
                    "command_state": "echo 1",
                    "command_timeout": 15,
                }
            },
            {
                "notify": {
                    "name": "Test",
                    "command": "echo 1",
                    "command_timeout": 15,
                }
            },
            {
                "sensor": {
                    "name": "Test",
                    "command": "echo 5",
                    "unit_of_measurement": "in",
                    "command_timeout": 15,
                }
            },
            {
                "switch": {
                    "name": "Test",
                    "command_state": "echo 1",
                    "command_timeout": 15,
                }
            },
        ]
    }


@pytest.fixture(name="load_yaml_integration")
async def load_int(menuai: menuai, get_config: dict[str, Any]) -> None:
    """Set up the Command Line integration in MenuAI."""
    await setup.async_setup_component(
        menuai,
        DOMAIN,
        get_config,
    )
    await menuai.async_block_till_done()
