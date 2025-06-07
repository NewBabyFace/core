"""Tests for the Nextcloud init."""

from unittest.mock import Mock, patch

from nextcloudmonitor import (
    NextcloudMonitorAuthorizationError,
    NextcloudMonitorConnectionError,
    NextcloudMonitorError,
    NextcloudMonitorRequestError,
)
import pytest

from menuai.components.nextcloud.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_URL, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import init_integration, mock_config_entry
from .const import MOCKED_ENTRY_ID, NC_DATA, VALID_CONFIG


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_async_setup_entry(
    menuai: menuai,
) -> None:
    """Test a successful setup entry."""
    assert await init_integration(menuai, VALID_CONFIG, NC_DATA)


async def test_unique_id_migration(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test migration of unique ids to stable ones."""

    object_id = "my_nc_url_local_system_version"
    entity_id = f"{Platform.SENSOR}.{object_id}"

    entry = mock_config_entry(VALID_CONFIG)
    entry.add_to_menuai(menuai)

    entity = entity_registry.async_get_or_create(
        Platform.SENSOR,
        DOMAIN,
        f"{VALID_CONFIG[CONF_URL]}#nextcloud_system_version",
        suggested_object_id=object_id,
        config_entry=entry,
    )

    # test old unique id
    assert entity.entity_id == entity_id
    assert entity.unique_id == f"{VALID_CONFIG[CONF_URL]}#nextcloud_system_version"

    with (
        patch(
            "menuai.components.nextcloud.NextcloudMonitor"
        ) as mock_nextcloud_monitor,
    ):
        mock_nextcloud_monitor.update = Mock(return_value=True)
        mock_nextcloud_monitor.return_value.data = NC_DATA
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    # test migrated unique id
    reg_entry = entity_registry.async_get(entity_id)
    assert reg_entry.unique_id == f"{MOCKED_ENTRY_ID}#system_version"


@pytest.mark.parametrize(
    ("exception", "expcted_entry_state"),
    [
        (NextcloudMonitorAuthorizationError, ConfigEntryState.SETUP_ERROR),
        (NextcloudMonitorConnectionError, ConfigEntryState.SETUP_RETRY),
        (NextcloudMonitorRequestError, ConfigEntryState.SETUP_RETRY),
    ],
)
async def test_setup_entry_errors(
    menuai: menuai,
    exception: NextcloudMonitorError,
    expcted_entry_state: ConfigEntryState,
) -> None:
    """Test a successful setup entry."""

    entry = mock_config_entry(VALID_CONFIG)
    entry.add_to_menuai(menuai)

    with (
        patch(
            "menuai.components.nextcloud.NextcloudMonitor", side_effect=exception
        ),
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()
        assert entry.state == expcted_entry_state
