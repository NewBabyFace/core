"""Test repairs handling for Sonos."""

from unittest.mock import Mock

from soco import SoCo

from menuai.components.sonos.const import (
    DOMAIN,
    SCAN_INTERVAL,
    SUB_FAIL_ISSUE_ID,
)
from menuai.core import menuai
from menuai.helpers import issue_registry as ir
from menuai.util import dt as dt_util

from .conftest import SonosMockEvent, SonosMockSubscribe

from tests.common import MockConfigEntry, async_fire_time_changed


async def test_subscription_repair_issues(
    menuai: menuai,
    config_entry: MockConfigEntry,
    soco: SoCo,
    zgs_discovery,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test repair issues handling for failed subscriptions."""
    subscription: SonosMockSubscribe = soco.zoneGroupTopology.subscribe.return_value
    subscription.event_listener = Mock(address=("192.168.4.2", 1400))

    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)

    # Ensure an issue is registered on subscription failure
    sub_callback = await subscription.wait_for_callback_to_be_set()
    async_fire_time_changed(menuai, dt_util.utcnow() + SCAN_INTERVAL)
    await menuai.async_block_till_done(wait_background_tasks=True)
    assert issue_registry.async_get_issue(DOMAIN, SUB_FAIL_ISSUE_ID)

    # Ensure the issue still exists after reload
    assert await menuai.config_entries.async_reload(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert issue_registry.async_get_issue(DOMAIN, SUB_FAIL_ISSUE_ID)

    # Ensure the issue has been removed after a successful subscription callback
    variables = {"ZoneGroupState": zgs_discovery}
    event = SonosMockEvent(soco, soco.zoneGroupTopology, variables)
    sub_callback(event)
    await menuai.async_block_till_done()
    assert not issue_registry.async_get_issue(DOMAIN, SUB_FAIL_ISSUE_ID)
    await menuai.async_block_till_done(wait_background_tasks=True)
