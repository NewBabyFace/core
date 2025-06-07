"""Test the Panasonic Viera setup process."""

from unittest.mock import Mock, patch

from menuai.components.panasonic_viera.const import (
    ATTR_DEVICE_INFO,
    ATTR_UDN,
    DEFAULT_NAME,
    DOMAIN,
)
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_HOST, STATE_UNAVAILABLE
from menuai.core import menuai
from menuai.setup import async_setup_component

from .conftest import (
    MOCK_CONFIG_DATA,
    MOCK_DEVICE_INFO,
    MOCK_ENCRYPTION_DATA,
    get_mock_remote,
)

from tests.common import MockConfigEntry


async def test_setup_entry_encrypted(menuai: menuai, mock_remote) -> None:
    """Test setup with encrypted config entry."""
    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_DEVICE_INFO[ATTR_UDN],
        data={**MOCK_CONFIG_DATA, **MOCK_ENCRYPTION_DATA, **MOCK_DEVICE_INFO},
    )

    mock_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(mock_entry.entry_id)
    await menuai.async_block_till_done()

    state_tv = menuai.states.get("media_player.panasonic_viera_tv")
    state_remote = menuai.states.get("remote.panasonic_viera_tv")

    assert state_tv
    assert state_tv.name == DEFAULT_NAME

    assert state_remote
    assert state_remote.name == DEFAULT_NAME


async def test_setup_entry_encrypted_missing_device_info(
    menuai: menuai, mock_remote
) -> None:
    """Test setup with encrypted config entry and missing device info."""
    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_CONFIG_DATA[CONF_HOST],
        data={**MOCK_CONFIG_DATA, **MOCK_ENCRYPTION_DATA},
    )

    mock_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(mock_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_entry.data[ATTR_DEVICE_INFO] == MOCK_DEVICE_INFO
    assert mock_entry.unique_id == MOCK_DEVICE_INFO[ATTR_UDN]

    state_tv = menuai.states.get("media_player.panasonic_viera_tv")
    state_remote = menuai.states.get("remote.panasonic_viera_tv")

    assert state_tv
    assert state_tv.name == DEFAULT_NAME

    assert state_remote
    assert state_remote.name == DEFAULT_NAME


async def test_setup_entry_encrypted_missing_device_info_none(
    menuai: menuai,
) -> None:
    """Test setup with encrypted config entry and device info set to None."""
    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_CONFIG_DATA[CONF_HOST],
        data={**MOCK_CONFIG_DATA, **MOCK_ENCRYPTION_DATA},
    )

    mock_entry.add_to_menuai(menuai)

    mock_remote = get_mock_remote(device_info=None)

    with patch(
        "menuai.components.panasonic_viera.RemoteControl",
        return_value=mock_remote,
    ):
        await menuai.config_entries.async_setup(mock_entry.entry_id)
        await menuai.async_block_till_done()

        assert mock_entry.data[ATTR_DEVICE_INFO] is None
        assert mock_entry.unique_id == MOCK_CONFIG_DATA[CONF_HOST]

        state_tv = menuai.states.get("media_player.panasonic_viera_tv")
        state_remote = menuai.states.get("remote.panasonic_viera_tv")

        assert state_tv
        assert state_tv.name == DEFAULT_NAME

        assert state_remote
        assert state_remote.name == DEFAULT_NAME


async def test_setup_entry_unencrypted(menuai: menuai, mock_remote) -> None:
    """Test setup with unencrypted config entry."""
    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_DEVICE_INFO[ATTR_UDN],
        data={**MOCK_CONFIG_DATA, **MOCK_DEVICE_INFO},
    )

    mock_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(mock_entry.entry_id)
    await menuai.async_block_till_done()

    state_tv = menuai.states.get("media_player.panasonic_viera_tv")
    state_remote = menuai.states.get("remote.panasonic_viera_tv")

    assert state_tv
    assert state_tv.name == DEFAULT_NAME

    assert state_remote
    assert state_remote.name == DEFAULT_NAME


async def test_setup_entry_unencrypted_missing_device_info(
    menuai: menuai, mock_remote
) -> None:
    """Test setup with unencrypted config entry and missing device info."""
    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_CONFIG_DATA[CONF_HOST],
        data={**MOCK_CONFIG_DATA},
    )

    mock_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(mock_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_entry.data[ATTR_DEVICE_INFO] == MOCK_DEVICE_INFO
    assert mock_entry.unique_id == MOCK_DEVICE_INFO[ATTR_UDN]

    state_tv = menuai.states.get("media_player.panasonic_viera_tv")
    state_remote = menuai.states.get("remote.panasonic_viera_tv")

    assert state_tv
    assert state_tv.name == DEFAULT_NAME

    assert state_remote
    assert state_remote.name == DEFAULT_NAME


async def test_setup_entry_unencrypted_missing_device_info_none(
    menuai: menuai,
) -> None:
    """Test setup with unencrypted config entry and device info set to None."""
    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_CONFIG_DATA[CONF_HOST],
        data={**MOCK_CONFIG_DATA},
    )

    mock_entry.add_to_menuai(menuai)

    mock_remote = get_mock_remote(device_info=None)

    with patch(
        "menuai.components.panasonic_viera.RemoteControl",
        return_value=mock_remote,
    ):
        await menuai.config_entries.async_setup(mock_entry.entry_id)
        await menuai.async_block_till_done()

        assert mock_entry.data[ATTR_DEVICE_INFO] is None
        assert mock_entry.unique_id == MOCK_CONFIG_DATA[CONF_HOST]

        state_tv = menuai.states.get("media_player.panasonic_viera_tv")
        state_remote = menuai.states.get("remote.panasonic_viera_tv")

        assert state_tv
        assert state_tv.name == DEFAULT_NAME

        assert state_remote
        assert state_remote.name == DEFAULT_NAME


async def test_setup_config_flow_initiated(menuai: menuai) -> None:
    """Test if config flow is initiated in setup."""
    mock_remote = get_mock_remote()
    mock_remote.get_device_info = Mock(side_effect=OSError)

    with patch(
        "menuai.components.panasonic_viera.config_flow.RemoteControl",
        return_value=mock_remote,
    ):
        assert (
            await async_setup_component(
                menuai,
                DOMAIN,
                {DOMAIN: {CONF_HOST: "0.0.0.0"}},
            )
            is True
        )

    assert len(menuai.config_entries.flow.async_progress()) == 1


async def test_setup_unload_entry(menuai: menuai, mock_remote) -> None:
    """Test if config entry is unloaded."""
    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_DEVICE_INFO[ATTR_UDN],
        data={**MOCK_CONFIG_DATA},
    )

    mock_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(mock_entry.entry_id)
    await menuai.async_block_till_done()

    await menuai.config_entries.async_unload(mock_entry.entry_id)
    assert mock_entry.state is ConfigEntryState.NOT_LOADED

    state_tv = menuai.states.get("media_player.panasonic_viera_tv")
    state_remote = menuai.states.get("remote.panasonic_viera_tv")

    assert state_tv.state == STATE_UNAVAILABLE
    assert state_remote.state == STATE_UNAVAILABLE

    await menuai.config_entries.async_remove(mock_entry.entry_id)
    await menuai.async_block_till_done()

    state_tv = menuai.states.get("media_player.panasonic_viera_tv")
    state_remote = menuai.states.get("remote.panasonic_viera_tv")

    assert state_tv is None
    assert state_remote is None
