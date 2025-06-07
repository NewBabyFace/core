"""Tests for component initialisation."""

from datetime import timedelta
from unittest.mock import AsyncMock

from freezegun.api import FrozenDateTimeFactory
from monzopy import AuthorisationExpiredError

from menuai.components.monzo.const import DOMAIN
from menuai.config_entries import SOURCE_REAUTH
from menuai.core import menuai

from . import setup_integration

from tests.common import MockConfigEntry, async_fire_time_changed


async def test_api_can_trigger_reauth(
    menuai: menuai,
    polling_config_entry: MockConfigEntry,
    monzo: AsyncMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test reauth an existing profile reauthenticates the config entry."""
    await setup_integration(menuai, polling_config_entry)

    monzo.user_account.accounts.side_effect = AuthorisationExpiredError()
    freezer.tick(timedelta(minutes=10))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    flows = menuai.config_entries.flow.async_progress()

    assert len(flows) == 1
    flow = flows[0]
    assert flow["step_id"] == "reauth_confirm"
    assert flow["handler"] == DOMAIN
    assert flow["context"]["source"] == SOURCE_REAUTH
