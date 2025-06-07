"""Tests for the CUPS sensor platform."""

from unittest.mock import patch

from menuai.components.cups import CONF_PRINTERS, DOMAIN
from menuai.components.sensor.const import DOMAIN as SENSOR_DOMAIN
from menuai.const import CONF_PLATFORM
from menuai.core import DOMAIN as menuai_DOMAIN, menuai
from menuai.helpers import issue_registry as ir
from menuai.setup import async_setup_component


async def test_repair_issue_is_created(
    menuai: menuai,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test repair issue is created."""
    with patch(
        "menuai.components.cups.sensor.CupsData", autospec=True
    ) as cups_data:
        cups_data.available = True
        assert await async_setup_component(
            menuai,
            SENSOR_DOMAIN,
            {
                SENSOR_DOMAIN: [
                    {
                        CONF_PLATFORM: DOMAIN,
                        CONF_PRINTERS: [
                            "printer1",
                        ],
                    }
                ],
            },
        )
        await menuai.async_block_till_done()
        assert (
            menuai_DOMAIN,
            f"deprecated_system_packages_yaml_integration_{DOMAIN}",
        ) in issue_registry.issues
