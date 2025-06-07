"""Test init."""

from unittest.mock import Mock, patch

from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_DEVICE
from menuai.core import DOMAIN as menuai_DOMAIN, menuai
from menuai.helpers import issue_registry as ir

from tests.common import MockConfigEntry


@patch.dict(
    "sys.modules",
    {
        "gammu": Mock(),
        "gammu.asyncworker": Mock(),
    },
)
async def test_repair_issue_is_created(
    menuai: menuai,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test repair issue is created."""
    from menuai.components.sms import (  # pylint: disable=import-outside-toplevel
        DEPRECATED_ISSUE_ID,
        DOMAIN,
    )

    with (
        patch("menuai.components.sms.create_sms_gateway", autospec=True),
        patch("menuai.components.sms.PLATFORMS", []),
    ):
        config_entry = MockConfigEntry(
            title="test",
            domain=DOMAIN,
            data={
                CONF_DEVICE: "/dev/ttyUSB0",
            },
        )

        config_entry.add_to_menuai(menuai)
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

        assert config_entry.state is ConfigEntryState.LOADED
        assert (
            menuai_DOMAIN,
            DEPRECATED_ISSUE_ID,
        ) in issue_registry.issues

        await menuai.config_entries.async_unload(config_entry.entry_id)
        await menuai.async_block_till_done()

        assert config_entry.state is ConfigEntryState.NOT_LOADED
        assert (
            menuai_DOMAIN,
            DEPRECATED_ISSUE_ID,
        ) not in issue_registry.issues
