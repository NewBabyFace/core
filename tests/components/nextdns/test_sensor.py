"""Test sensor of NextDNS integration."""

from datetime import timedelta
from unittest.mock import patch

from nextdns import ApiError
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.const import STATE_UNAVAILABLE, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.util.dt import utcnow

from . import init_integration, mock_nextdns

from tests.common import async_fire_time_changed, snapshot_platform


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensor(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test states of sensors."""
    with patch("menuai.components.nextdns.PLATFORMS", [Platform.SENSOR]):
        entry = await init_integration(menuai)

    await snapshot_platform(menuai, entity_registry, snapshot, entry.entry_id)


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_availability(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
) -> None:
    """Ensure that we mark the entities unavailable correctly when service causes an error."""
    await init_integration(menuai)

    state = menuai.states.get("sensor.fake_profile_dns_queries")
    assert state
    assert state.state != STATE_UNAVAILABLE
    assert state.state == "100"

    state = menuai.states.get("sensor.fake_profile_dns_over_https_queries")
    assert state
    assert state.state != STATE_UNAVAILABLE
    assert state.state == "20"

    state = menuai.states.get("sensor.fake_profile_dnssec_validated_queries")
    assert state
    assert state.state != STATE_UNAVAILABLE
    assert state.state == "75"

    state = menuai.states.get("sensor.fake_profile_encrypted_queries")
    assert state
    assert state.state != STATE_UNAVAILABLE
    assert state.state == "60"

    state = menuai.states.get("sensor.fake_profile_ipv4_queries")
    assert state
    assert state.state != STATE_UNAVAILABLE
    assert state.state == "90"

    future = utcnow() + timedelta(minutes=10)
    with (
        patch(
            "menuai.components.nextdns.NextDns.get_analytics_status",
            side_effect=ApiError("API Error"),
        ),
        patch(
            "menuai.components.nextdns.NextDns.get_analytics_dnssec",
            side_effect=ApiError("API Error"),
        ),
        patch(
            "menuai.components.nextdns.NextDns.get_analytics_encryption",
            side_effect=ApiError("API Error"),
        ),
        patch(
            "menuai.components.nextdns.NextDns.get_analytics_ip_versions",
            side_effect=ApiError("API Error"),
        ),
        patch(
            "menuai.components.nextdns.NextDns.get_analytics_protocols",
            side_effect=ApiError("API Error"),
        ),
    ):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done(wait_background_tasks=True)

    state = menuai.states.get("sensor.fake_profile_dns_queries")
    assert state
    assert state.state == STATE_UNAVAILABLE

    state = menuai.states.get("sensor.fake_profile_dns_over_https_queries")
    assert state
    assert state.state == STATE_UNAVAILABLE

    state = menuai.states.get("sensor.fake_profile_dnssec_validated_queries")
    assert state
    assert state.state == STATE_UNAVAILABLE

    state = menuai.states.get("sensor.fake_profile_encrypted_queries")
    assert state
    assert state.state == STATE_UNAVAILABLE

    state = menuai.states.get("sensor.fake_profile_ipv4_queries")
    assert state
    assert state.state == STATE_UNAVAILABLE

    future = utcnow() + timedelta(minutes=20)
    with mock_nextdns():
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done(wait_background_tasks=True)

    state = menuai.states.get("sensor.fake_profile_dns_queries")
    assert state
    assert state.state != STATE_UNAVAILABLE
    assert state.state == "100"

    state = menuai.states.get("sensor.fake_profile_dns_over_https_queries")
    assert state
    assert state.state != STATE_UNAVAILABLE
    assert state.state == "20"

    state = menuai.states.get("sensor.fake_profile_dnssec_validated_queries")
    assert state
    assert state.state != STATE_UNAVAILABLE
    assert state.state == "75"

    state = menuai.states.get("sensor.fake_profile_encrypted_queries")
    assert state
    assert state.state != STATE_UNAVAILABLE
    assert state.state == "60"

    state = menuai.states.get("sensor.fake_profile_ipv4_queries")
    assert state
    assert state.state != STATE_UNAVAILABLE
    assert state.state == "90"
