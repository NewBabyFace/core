"""Fixtures for Risco tests."""

from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import MagicMock, PropertyMock, patch

from pyrisco.cloud.event import Event
import pytest

from menuai.components.risco.const import DOMAIN, TYPE_LOCAL
from menuai.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PIN,
    CONF_PORT,
    CONF_TYPE,
    CONF_USERNAME,
)
from menuai.core import menuai

from .util import TEST_SITE_NAME, TEST_SITE_UUID, system_mock, zone_mock

from tests.common import MockConfigEntry

TEST_CLOUD_CONFIG = {
    CONF_USERNAME: "test-username",
    CONF_PASSWORD: "test-password",
    CONF_PIN: "1234",
}
TEST_LOCAL_CONFIG = {
    CONF_TYPE: TYPE_LOCAL,
    CONF_HOST: "test-host",
    CONF_PORT: 5004,
    CONF_PIN: "1234",
}


@pytest.fixture
def two_zone_cloud():
    """Fixture to mock alarm with two zones."""
    zone_mocks = {0: zone_mock(), 1: zone_mock()}
    alarm_mock = MagicMock()
    with (
        patch.object(zone_mocks[0], "id", new_callable=PropertyMock(return_value=0)),
        patch.object(
            zone_mocks[0], "name", new_callable=PropertyMock(return_value="Zone 0")
        ),
        patch.object(
            zone_mocks[0], "bypassed", new_callable=PropertyMock(return_value=False)
        ),
        patch.object(zone_mocks[1], "id", new_callable=PropertyMock(return_value=1)),
        patch.object(
            zone_mocks[1], "name", new_callable=PropertyMock(return_value="Zone 1")
        ),
        patch.object(
            zone_mocks[1], "bypassed", new_callable=PropertyMock(return_value=False)
        ),
        patch.object(
            alarm_mock,
            "zones",
            new_callable=PropertyMock(return_value=zone_mocks),
        ),
        patch(
            "menuai.components.risco.RiscoCloud.get_state",
            return_value=alarm_mock,
        ),
    ):
        yield zone_mocks


@pytest.fixture
def two_zone_local():
    """Fixture to mock alarm with two zones."""
    zone_mocks = {0: zone_mock(), 1: zone_mock()}
    system = system_mock()
    with (
        patch.object(zone_mocks[0], "id", new_callable=PropertyMock(return_value=0)),
        patch.object(
            zone_mocks[0], "name", new_callable=PropertyMock(return_value="Zone 0")
        ),
        patch.object(
            zone_mocks[0], "alarmed", new_callable=PropertyMock(return_value=False)
        ),
        patch.object(
            zone_mocks[0], "bypassed", new_callable=PropertyMock(return_value=False)
        ),
        patch.object(
            zone_mocks[0], "armed", new_callable=PropertyMock(return_value=False)
        ),
        patch.object(zone_mocks[1], "id", new_callable=PropertyMock(return_value=1)),
        patch.object(
            zone_mocks[1], "name", new_callable=PropertyMock(return_value="Zone 1")
        ),
        patch.object(
            zone_mocks[1], "alarmed", new_callable=PropertyMock(return_value=False)
        ),
        patch.object(
            zone_mocks[1], "bypassed", new_callable=PropertyMock(return_value=False)
        ),
        patch.object(
            zone_mocks[1], "armed", new_callable=PropertyMock(return_value=False)
        ),
        patch.object(
            system, "name", new_callable=PropertyMock(return_value=TEST_SITE_NAME)
        ),
        patch(
            "menuai.components.risco.RiscoLocal.partitions",
            new_callable=PropertyMock(return_value={}),
        ),
        patch(
            "menuai.components.risco.RiscoLocal.zones",
            new_callable=PropertyMock(return_value=zone_mocks),
        ),
        patch(
            "menuai.components.risco.RiscoLocal.system",
            new_callable=PropertyMock(return_value=system),
        ),
    ):
        yield zone_mocks


@pytest.fixture
def options() -> dict[str, Any]:
    """Fixture for default (empty) options."""
    return {}


@pytest.fixture
def events() -> list[Event]:
    """Fixture for default (empty) events."""
    return []


@pytest.fixture
def cloud_config_entry(menuai: menuai, options: dict[str, Any]) -> MockConfigEntry:
    """Fixture for a cloud config entry."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=TEST_CLOUD_CONFIG,
        options=options,
        unique_id=TEST_CLOUD_CONFIG[CONF_USERNAME],
    )
    config_entry.add_to_menuai(menuai)
    return config_entry


@pytest.fixture
def login_with_error(exception):
    """Fixture to simulate error on login."""
    with patch(
        "menuai.components.risco.RiscoCloud.login",
        side_effect=exception,
    ):
        yield


@pytest.fixture
async def setup_risco_cloud(
    menuai: menuai, cloud_config_entry: MockConfigEntry, events: list[Event]
) -> AsyncGenerator[MockConfigEntry]:
    """Set up a Risco integration for testing."""
    with (
        patch(
            "menuai.components.risco.RiscoCloud.login",
            return_value=True,
        ),
        patch(
            "menuai.components.risco.RiscoCloud.site_uuid",
            new_callable=PropertyMock(return_value=TEST_SITE_UUID),
        ),
        patch(
            "menuai.components.risco.RiscoCloud.site_name",
            new_callable=PropertyMock(return_value=TEST_SITE_NAME),
        ),
        patch(
            "menuai.components.risco.RiscoCloud.close",
        ),
        patch(
            "menuai.components.risco.RiscoCloud.get_events",
            return_value=events,
        ),
    ):
        await menuai.config_entries.async_setup(cloud_config_entry.entry_id)
        await menuai.async_block_till_done()

        yield cloud_config_entry


@pytest.fixture
def local_config_entry(menuai: menuai, options: dict[str, Any]) -> MockConfigEntry:
    """Fixture for a local config entry."""
    config_entry = MockConfigEntry(
        domain=DOMAIN, data=TEST_LOCAL_CONFIG, options=options
    )
    config_entry.add_to_menuai(menuai)
    return config_entry


@pytest.fixture
def connect_with_error(exception):
    """Fixture to simulate error on connect."""
    with patch(
        "menuai.components.risco.RiscoLocal.connect",
        side_effect=exception,
    ):
        yield


@pytest.fixture
async def setup_risco_local(
    menuai: menuai, local_config_entry: MockConfigEntry
) -> AsyncGenerator[MockConfigEntry]:
    """Set up a local Risco integration for testing."""
    with (
        patch(
            "menuai.components.risco.RiscoLocal.connect",
            return_value=True,
        ),
        patch(
            "menuai.components.risco.RiscoLocal.id",
            new_callable=PropertyMock(return_value=TEST_SITE_UUID),
        ),
        patch(
            "menuai.components.risco.RiscoLocal.disconnect",
        ),
    ):
        await menuai.config_entries.async_setup(local_config_entry.entry_id)
        await menuai.async_block_till_done()

        yield local_config_entry
