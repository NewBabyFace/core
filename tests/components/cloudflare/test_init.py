"""Test the Cloudflare integration."""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pycfdns
import pytest

from menuai.components.cloudflare.const import (
    CONF_RECORDS,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    SERVICE_UPDATE_RECORDS,
)
from menuai.config_entries import SOURCE_REAUTH, ConfigEntryState
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.util import dt as dt_util
from menuai.util.location import LocationInfo

from . import ENTRY_CONFIG, init_integration

from tests.common import MockConfigEntry, async_fire_time_changed


async def test_unload_entry(menuai: menuai, cfupdate: MagicMock) -> None:
    """Test successful unload of entry."""
    entry = await init_integration(menuai)

    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state is ConfigEntryState.LOADED

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert not menuai.data.get(DOMAIN)


@pytest.mark.parametrize(
    "side_effect",
    [pycfdns.ComunicationException()],
)
async def test_async_setup_raises_entry_not_ready(
    menuai: menuai, cfupdate: MagicMock, side_effect: Exception
) -> None:
    """Test that it throws ConfigEntryNotReady when exception occurs during setup."""
    instance = cfupdate.return_value

    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_CONFIG)
    entry.add_to_menuai(menuai)

    instance.list_zones.side_effect = side_effect
    await menuai.config_entries.async_setup(entry.entry_id)

    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_async_setup_raises_entry_auth_failed(
    menuai: menuai, cfupdate: MagicMock
) -> None:
    """Test that it throws ConfigEntryAuthFailed when exception occurs during setup."""
    instance = cfupdate.return_value

    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_CONFIG)
    entry.add_to_menuai(menuai)

    instance.list_zones.side_effect = pycfdns.AuthenticationException()
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_ERROR

    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 1

    flow = flows[0]
    assert flow["step_id"] == "reauth_confirm"
    assert flow["handler"] == DOMAIN

    assert "context" in flow
    assert flow["context"]["source"] == SOURCE_REAUTH
    assert flow["context"]["entry_id"] == entry.entry_id


async def test_integration_services(
    menuai: menuai, cfupdate: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    """Test integration services."""
    instance = cfupdate.return_value

    entry = await init_integration(menuai)
    assert entry.state is ConfigEntryState.LOADED

    with patch(
        "menuai.components.cloudflare.async_detect_location_info",
        return_value=LocationInfo(
            "0.0.0.0",
            "US",
            "USD",
            "CA",
            "California",
            "San Diego",
            "92122",
            "America/Los_Angeles",
            32.8594,
            -117.2073,
            True,
        ),
    ):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_UPDATE_RECORDS,
            {},
            blocking=True,
        )
        await menuai.async_block_till_done()

    assert len(instance.update_dns_record.mock_calls) == 2
    assert "All target records are up to date" not in caplog.text


async def test_integration_services_with_issue(
    menuai: menuai, cfupdate: MagicMock
) -> None:
    """Test integration services with issue."""
    instance = cfupdate.return_value

    entry = await init_integration(menuai)
    assert entry.state is ConfigEntryState.LOADED

    with (
        patch(
            "menuai.components.cloudflare.async_detect_location_info",
            return_value=None,
        ),
        pytest.raises(menuaiError, match="Could not get external IPv4 address"),
    ):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_UPDATE_RECORDS,
            {},
            blocking=True,
        )

    instance.update_dns_record.assert_not_called()


async def test_integration_services_with_nonexisting_record(
    menuai: menuai, cfupdate: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    """Test integration services."""
    instance = cfupdate.return_value

    entry = await init_integration(
        menuai, data={**ENTRY_CONFIG, CONF_RECORDS: ["nonexisting.example.com"]}
    )
    assert entry.state is ConfigEntryState.LOADED

    with patch(
        "menuai.components.cloudflare.async_detect_location_info",
        return_value=LocationInfo(
            "0.0.0.0",
            "US",
            "USD",
            "CA",
            "California",
            "San Diego",
            "92122",
            "America/Los_Angeles",
            32.8594,
            -117.2073,
            True,
        ),
    ):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_UPDATE_RECORDS,
            {},
            blocking=True,
        )
        await menuai.async_block_till_done()

    instance.update_dns_record.assert_not_called()
    assert "All target records are up to date" in caplog.text


async def test_integration_update_interval(
    menuai: menuai,
    cfupdate: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test integration update interval."""
    instance = cfupdate.return_value

    entry = await init_integration(menuai)
    assert entry.state is ConfigEntryState.LOADED

    with patch(
        "menuai.components.cloudflare.async_detect_location_info",
        return_value=LocationInfo(
            "0.0.0.0",
            "US",
            "USD",
            "CA",
            "California",
            "San Diego",
            "92122",
            "America/Los_Angeles",
            32.8594,
            -117.2073,
            True,
        ),
    ):
        async_fire_time_changed(
            menuai, dt_util.utcnow() + timedelta(minutes=DEFAULT_UPDATE_INTERVAL)
        )
        await menuai.async_block_till_done(wait_background_tasks=True)
        assert len(instance.update_dns_record.mock_calls) == 2
        assert "All target records are up to date" not in caplog.text

        instance.list_dns_records.side_effect = pycfdns.AuthenticationException()
        async_fire_time_changed(
            menuai, dt_util.utcnow() + timedelta(minutes=DEFAULT_UPDATE_INTERVAL)
        )
        await menuai.async_block_till_done(wait_background_tasks=True)
        assert len(instance.update_dns_record.mock_calls) == 2

        instance.list_dns_records.side_effect = pycfdns.ComunicationException()
        async_fire_time_changed(
            menuai, dt_util.utcnow() + timedelta(minutes=DEFAULT_UPDATE_INTERVAL)
        )
        await menuai.async_block_till_done(wait_background_tasks=True)
        assert len(instance.update_dns_record.mock_calls) == 2
