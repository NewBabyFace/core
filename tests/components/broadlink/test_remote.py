"""Tests for Broadlink remotes."""

from base64 import b64decode
from unittest.mock import call

from menuai.components.broadlink.const import DOMAIN
from menuai.components.remote import (
    DOMAIN as REMOTE_DOMAIN,
    SERVICE_SEND_COMMAND,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from menuai.const import ATTR_FRIENDLY_NAME, STATE_OFF, STATE_ON, Platform
from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er

from . import get_device

REMOTE_DEVICES = ["Entrance", "Living Room", "Office", "Garage"]

IR_PACKET = (
    "JgBGAJKVETkRORA6ERQRFBEUERQRFBE5ETkQOhAVEBUQFREUEBUQ"
    "OhEUERQRORE5EBURFBA6EBUQOhE5EBUQFRA6EDoRFBEADQUAAA=="
)


async def test_remote_setup_works(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test a successful setup with all remotes."""
    for device in map(get_device, REMOTE_DEVICES):
        mock_setup = await device.setup_entry(menuai)

        device_entry = device_registry.async_get_device(
            identifiers={(DOMAIN, mock_setup.entry.unique_id)}
        )
        entries = er.async_entries_for_device(entity_registry, device_entry.id)
        remotes = [entry for entry in entries if entry.domain == Platform.REMOTE]
        assert len(remotes) == 1

        remote = remotes[0]
        assert (
            menuai.states.get(remote.entity_id).attributes[ATTR_FRIENDLY_NAME]
            == device.name
        )
        assert menuai.states.get(remote.entity_id).state == STATE_ON
        assert mock_setup.api.auth.call_count == 1


async def test_remote_send_command(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test sending a command with all remotes."""
    for device in map(get_device, REMOTE_DEVICES):
        mock_setup = await device.setup_entry(menuai)

        device_entry = device_registry.async_get_device(
            identifiers={(DOMAIN, mock_setup.entry.unique_id)}
        )
        entries = er.async_entries_for_device(entity_registry, device_entry.id)
        remotes = [entry for entry in entries if entry.domain == Platform.REMOTE]
        assert len(remotes) == 1

        remote = remotes[0]
        await menuai.services.async_call(
            REMOTE_DOMAIN,
            SERVICE_SEND_COMMAND,
            {"entity_id": remote.entity_id, "command": "b64:" + IR_PACKET},
            blocking=True,
        )

        assert mock_setup.api.send_data.call_count == 1
        assert mock_setup.api.send_data.call_args == call(b64decode(IR_PACKET))
        assert mock_setup.api.auth.call_count == 1


async def test_remote_turn_off_turn_on(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test we do not send commands if the remotes are off."""
    for device in map(get_device, REMOTE_DEVICES):
        mock_setup = await device.setup_entry(menuai)

        device_entry = device_registry.async_get_device(
            identifiers={(DOMAIN, mock_setup.entry.unique_id)}
        )
        entries = er.async_entries_for_device(entity_registry, device_entry.id)
        remotes = [entry for entry in entries if entry.domain == Platform.REMOTE]
        assert len(remotes) == 1

        remote = remotes[0]
        await menuai.services.async_call(
            REMOTE_DOMAIN,
            SERVICE_TURN_OFF,
            {"entity_id": remote.entity_id},
            blocking=True,
        )
        assert menuai.states.get(remote.entity_id).state == STATE_OFF

        await menuai.services.async_call(
            REMOTE_DOMAIN,
            SERVICE_SEND_COMMAND,
            {"entity_id": remote.entity_id, "command": "b64:" + IR_PACKET},
            blocking=True,
        )
        assert mock_setup.api.send_data.call_count == 0

        await menuai.services.async_call(
            REMOTE_DOMAIN,
            SERVICE_TURN_ON,
            {"entity_id": remote.entity_id},
            blocking=True,
        )
        assert menuai.states.get(remote.entity_id).state == STATE_ON

        await menuai.services.async_call(
            REMOTE_DOMAIN,
            SERVICE_SEND_COMMAND,
            {"entity_id": remote.entity_id, "command": "b64:" + IR_PACKET},
            blocking=True,
        )
        assert mock_setup.api.send_data.call_count == 1
        assert mock_setup.api.send_data.call_args == call(b64decode(IR_PACKET))
        assert mock_setup.api.auth.call_count == 1
