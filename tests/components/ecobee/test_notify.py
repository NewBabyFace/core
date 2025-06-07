"""Test Ecobee notify service."""

from unittest.mock import MagicMock

from menuai.components.notify import (
    DOMAIN as NOTIFY_DOMAIN,
    SERVICE_SEND_MESSAGE,
)
from menuai.core import menuai

from .common import setup_platform

THERMOSTAT_ID = 0


async def test_notify_entity_service(
    menuai: menuai,
    mock_ecobee: MagicMock,
) -> None:
    """Test the notify entity service."""
    await setup_platform(menuai, NOTIFY_DOMAIN)

    entity_id = "notify.ecobee"
    state = menuai.states.get(entity_id)
    assert state is not None
    assert menuai.services.has_service(NOTIFY_DOMAIN, SERVICE_SEND_MESSAGE)
    await menuai.services.async_call(
        NOTIFY_DOMAIN,
        SERVICE_SEND_MESSAGE,
        service_data={"entity_id": entity_id, "message": "It is too cold!"},
        blocking=True,
    )
    await menuai.async_block_till_done()
    mock_ecobee.send_message.assert_called_with(THERMOSTAT_ID, "It is too cold!")
