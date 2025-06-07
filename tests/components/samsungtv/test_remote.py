"""The tests for the SamsungTV remote platform."""

from unittest.mock import Mock, patch

import pytest
from samsungtvws.encrypted.remote import SamsungTVEncryptedCommand

from menuai.components.remote import (
    ATTR_COMMAND,
    DOMAIN as REMOTE_DOMAIN,
    SERVICE_SEND_COMMAND,
)
from menuai.components.samsungtv.const import DOMAIN
from menuai.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF, SERVICE_TURN_ON
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er

from . import setup_samsungtv_entry
from .const import ENTRYDATA_ENCRYPTED_WEBSOCKET, ENTRYDATA_LEGACY, ENTRYDATA_WEBSOCKET

from tests.common import MockConfigEntry

ENTITY_ID = f"{REMOTE_DOMAIN}.mock_title"


@pytest.mark.usefixtures("remote_encrypted_websocket", "rest_api")
async def test_setup(menuai: menuai) -> None:
    """Test setup with basic config."""
    await setup_samsungtv_entry(menuai, ENTRYDATA_ENCRYPTED_WEBSOCKET)
    assert menuai.states.get(ENTITY_ID)


@pytest.mark.usefixtures("remote_encrypted_websocket", "rest_api")
async def test_unique_id(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test unique id."""
    await setup_samsungtv_entry(menuai, ENTRYDATA_ENCRYPTED_WEBSOCKET)

    main = entity_registry.async_get(ENTITY_ID)
    assert main.unique_id == "be9554b9-c9fb-41f4-8920-22da015376a4"


@pytest.mark.usefixtures("remote_encrypted_websocket", "rest_api")
async def test_main_services(
    menuai: menuai,
    remote_encrypted_websocket: Mock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test for turn_off."""
    await setup_samsungtv_entry(menuai, ENTRYDATA_ENCRYPTED_WEBSOCKET)

    remote_encrypted_websocket.send_commands.reset_mock()

    await menuai.services.async_call(
        REMOTE_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: ENTITY_ID},
        blocking=True,
    )

    # key called
    assert remote_encrypted_websocket.send_commands.call_count == 1
    commands = remote_encrypted_websocket.send_commands.call_args_list[0].args[0]
    assert len(commands) == 2
    assert isinstance(command := commands[0], SamsungTVEncryptedCommand)
    assert command.body["param3"] == "KEY_POWEROFF"
    assert isinstance(command := commands[1], SamsungTVEncryptedCommand)
    assert command.body["param3"] == "KEY_POWER"

    # commands not sent : power off in progress
    remote_encrypted_websocket.send_commands.reset_mock()
    await menuai.services.async_call(
        REMOTE_DOMAIN,
        SERVICE_SEND_COMMAND,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_COMMAND: ["dash"]},
        blocking=True,
    )
    assert "TV is powering off, not sending keys: ['dash']" in caplog.text
    remote_encrypted_websocket.send_commands.assert_not_called()


@pytest.mark.usefixtures("remote_encrypted_websocket", "rest_api")
async def test_send_command_service(
    menuai: menuai, remote_encrypted_websocket: Mock
) -> None:
    """Test the send command."""
    await setup_samsungtv_entry(menuai, ENTRYDATA_ENCRYPTED_WEBSOCKET)

    await menuai.services.async_call(
        REMOTE_DOMAIN,
        SERVICE_SEND_COMMAND,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_COMMAND: ["dash"]},
        blocking=True,
    )

    assert remote_encrypted_websocket.send_commands.call_count == 1
    commands = remote_encrypted_websocket.send_commands.call_args_list[0].args[0]
    assert len(commands) == 1
    assert isinstance(command := commands[0], SamsungTVEncryptedCommand)
    assert command.body["param3"] == "dash"


@pytest.mark.usefixtures("remote_websocket", "rest_api")
async def test_turn_on_wol(menuai: menuai) -> None:
    """Test turn on."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=ENTRYDATA_WEBSOCKET,
        unique_id="be9554b9-c9fb-41f4-8920-22da015376a4",
    )
    entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    with patch(
        "menuai.components.samsungtv.entity.send_magic_packet"
    ) as mock_send_magic_packet:
        await menuai.services.async_call(
            REMOTE_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: ENTITY_ID}, True
        )
        await menuai.async_block_till_done()
    assert mock_send_magic_packet.called


async def test_turn_on_without_turnon(menuai: menuai, remote_legacy: Mock) -> None:
    """Test turn on."""
    await setup_samsungtv_entry(menuai, ENTRYDATA_LEGACY)
    with pytest.raises(menuaiError) as exc_info:
        await menuai.services.async_call(
            REMOTE_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: ENTITY_ID}, True
        )
    # nothing called as not supported feature
    assert remote_legacy.control.call_count == 0
    assert exc_info.value.translation_domain == DOMAIN
    assert exc_info.value.translation_key == "service_unsupported"
    assert exc_info.value.translation_placeholders == {
        "entity": ENTITY_ID,
    }
