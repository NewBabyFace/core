"""Test the HTML5 setup."""

from menuai.core import menuai
from menuai.helpers import issue_registry as ir
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry

NOTIFY_CONF = {
    "notify": [
        {
            "platform": "html5",
            "name": "html5",
            "vapid_pub_key": "BIUtPN7Rq_8U7RBEqClZrfZ5dR9zPCfvxYPtLpWtRVZTJEc7lzv2dhzDU6Aw1m29Ao0-UA1Uq6XO9Df8KALBKqA",
            "vapid_prv_key": "h6acSRds8_KR8hT9djD8WucTL06Gfe29XXyZ1KcUjN8",
            "vapid_email": "test@example.com",
        }
    ]
}


async def test_setup_entry(
    menuai: menuai,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test setup of a good config entry."""
    config_entry = MockConfigEntry(domain="html5", data={})
    config_entry.add_to_menuai(menuai)
    assert await async_setup_component(menuai, "html5", {})

    assert len(issue_registry.issues) == 0


async def test_setup_entry_issue(
    menuai: menuai,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test setup of an imported config entry with deprecated YAML."""
    config_entry = MockConfigEntry(domain="html5", data={})
    config_entry.add_to_menuai(menuai)
    assert await async_setup_component(menuai, "notify", NOTIFY_CONF)
    assert await async_setup_component(menuai, "html5", NOTIFY_CONF)

    assert len(issue_registry.issues) == 1
