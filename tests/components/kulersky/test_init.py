"""Tests for init methods."""

from menuai.components.kulersky.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_ADDRESS
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from tests.common import MockConfigEntry


async def test_migrate_entry(
    menuai: menuai,
) -> None:
    """Test migrate config entry from v1 to v2."""

    mock_config_entry_v1 = MockConfigEntry(
        version=1,
        domain=DOMAIN,
        title="KulerSky",
    )

    mock_config_entry_v1.add_to_menuai(menuai)

    dev_reg = dr.async_get(menuai)
    # Create device registry entries for old integration
    dev_reg.async_get_or_create(
        config_entry_id=mock_config_entry_v1.entry_id,
        identifiers={(DOMAIN, "AA:BB:CC:11:22:33")},
        name="KuLight 1",
    )
    dev_reg.async_get_or_create(
        config_entry_id=mock_config_entry_v1.entry_id,
        identifiers={(DOMAIN, "AA:BB:CC:44:55:66")},
        name="KuLight 2",
    )
    await menuai.config_entries.async_setup(mock_config_entry_v1.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry_v1.state is ConfigEntryState.SETUP_RETRY
    assert mock_config_entry_v1.version == 2
    assert mock_config_entry_v1.unique_id == "AA:BB:CC:11:22:33"
    assert mock_config_entry_v1.data == {
        CONF_ADDRESS: "AA:BB:CC:11:22:33",
    }


async def test_migrate_entry_no_devices_found(
    menuai: menuai,
) -> None:
    """Test migrate config entry from v1 to v2."""

    mock_config_entry_v1 = MockConfigEntry(
        version=1,
        domain=DOMAIN,
        title="KulerSky",
    )

    mock_config_entry_v1.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(mock_config_entry_v1.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry_v1.state is ConfigEntryState.MIGRATION_ERROR
    assert mock_config_entry_v1.version == 1
