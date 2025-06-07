"""Test the Reolink button platform."""

from unittest.mock import MagicMock, patch

import pytest
from reolink_aio.exceptions import ReolinkError

from menuai.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from menuai.components.reolink.button import ATTR_SPEED, SERVICE_PTZ_MOVE
from menuai.components.reolink.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.exceptions import menuaiError

from .conftest import TEST_NVR_NAME

from tests.common import MockConfigEntry


async def test_button(
    menuai: menuai,
    config_entry: MockConfigEntry,
    reolink_connect: MagicMock,
) -> None:
    """Test button entity with ptz up."""
    with patch("menuai.components.reolink.PLATFORMS", [Platform.BUTTON]):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED

    entity_id = f"{Platform.BUTTON}.{TEST_NVR_NAME}_ptz_up"

    await menuai.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    reolink_connect.set_ptz_command.assert_called_once()

    reolink_connect.set_ptz_command.side_effect = ReolinkError("Test error")
    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )

    reolink_connect.set_ptz_command.reset_mock(side_effect=True)


async def test_ptz_move_service(
    menuai: menuai,
    config_entry: MockConfigEntry,
    reolink_connect: MagicMock,
) -> None:
    """Test ptz_move entity service using PTZ button entity."""
    with patch("menuai.components.reolink.PLATFORMS", [Platform.BUTTON]):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED

    entity_id = f"{Platform.BUTTON}.{TEST_NVR_NAME}_ptz_up"

    await menuai.services.async_call(
        DOMAIN,
        SERVICE_PTZ_MOVE,
        {ATTR_ENTITY_ID: entity_id, ATTR_SPEED: 5},
        blocking=True,
    )
    reolink_connect.set_ptz_command.assert_called_with(0, command="Up", speed=5)

    reolink_connect.set_ptz_command.side_effect = ReolinkError("Test error")
    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_PTZ_MOVE,
            {ATTR_ENTITY_ID: entity_id, ATTR_SPEED: 5},
            blocking=True,
        )

    reolink_connect.set_ptz_command.reset_mock(side_effect=True)


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_host_button(
    menuai: menuai,
    config_entry: MockConfigEntry,
    reolink_connect: MagicMock,
) -> None:
    """Test host button entity with reboot."""
    with patch("menuai.components.reolink.PLATFORMS", [Platform.BUTTON]):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED

    entity_id = f"{Platform.BUTTON}.{TEST_NVR_NAME}_restart"

    await menuai.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    reolink_connect.reboot.assert_called_once()

    reolink_connect.reboot.side_effect = ReolinkError("Test error")
    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )

    reolink_connect.reboot.reset_mock(side_effect=True)
