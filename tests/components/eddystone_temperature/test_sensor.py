"""Tests for eddystone temperature."""

from unittest.mock import Mock, patch

from menuai.components.eddystone_temperature import (
    CONF_BEACONS,
    CONF_INSTANCE,
    CONF_NAMESPACE,
    DOMAIN,
)
from menuai.components.sensor import DOMAIN as PLATFORM_DOMAIN
from menuai.const import CONF_PLATFORM
from menuai.core import DOMAIN as menuai_DOMAIN, menuai
from menuai.helpers import issue_registry as ir
from menuai.setup import async_setup_component


@patch.dict("sys.modules", beacontools=Mock())
async def test_repair_issue_is_created(
    menuai: menuai,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test repair issue is created."""
    assert await async_setup_component(
        menuai,
        PLATFORM_DOMAIN,
        {
            PLATFORM_DOMAIN: [
                {
                    CONF_PLATFORM: DOMAIN,
                    CONF_BEACONS: {
                        "living_room": {
                            CONF_NAMESPACE: "112233445566778899AA",
                            CONF_INSTANCE: "000000000001",
                        }
                    },
                }
            ],
        },
    )
    await menuai.async_block_till_done()
    assert (
        menuai_DOMAIN,
        f"deprecated_system_packages_yaml_integration_{DOMAIN}",
    ) in issue_registry.issues
