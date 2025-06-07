"""Test SIP server."""

import socket

import pytest

from menuai import config_entries
from menuai.components import voip
from menuai.core import menuai


@pytest.mark.usefixtures("socket_enabled")
async def test_create_sip_server(menuai: menuai) -> None:
    """Tests starting/stopping SIP server."""
    result = await menuai.config_entries.flow.async_init(
        voip.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {},
    )
    entry = result["result"]
    await menuai.async_block_till_done()

    with (
        pytest.raises(OSError),
        socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock,
    ):
        # Server should have the port
        sock.bind(("127.0.0.1", 5060))

    # Configure different port
    result = await menuai.config_entries.options.async_init(
        entry.entry_id,
    )
    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"sip_port": 5061},
    )
    await menuai.async_block_till_done()

    # Server should be stopped now on 5060
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 5060))

    with (
        pytest.raises(OSError),
        socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock,
    ):
        # Server should now have the new port
        sock.bind(("127.0.0.1", 5061))

    # Shut down
    await menuai.config_entries.async_remove(entry.entry_id)
    await menuai.async_block_till_done()

    # Server should be stopped
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 5061))
