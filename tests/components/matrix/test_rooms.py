"""Test MatrixBot._join."""

import pytest

from menuai.components.matrix import MatrixBot
from menuai.components.matrix.const import DOMAIN
from menuai.components.notify import DOMAIN as NOTIFY_DOMAIN
from menuai.const import EVENT_menuai_START
from menuai.core import menuai
from menuai.setup import async_setup_component

from .conftest import MOCK_CONFIG_DATA, TEST_BAD_ROOM, TEST_JOINABLE_ROOMS


async def test_join(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
    mock_client,
    mock_save_json,
    mock_allowed_path,
) -> None:
    """Test joining configured rooms."""
    assert await async_setup_component(menuai, DOMAIN, MOCK_CONFIG_DATA)
    assert await async_setup_component(menuai, NOTIFY_DOMAIN, MOCK_CONFIG_DATA)
    menuai.bus.async_fire(EVENT_menuai_START)
    await menuai.async_block_till_done(wait_background_tasks=True)

    # Accessing menuai.data in tests is not desirable, but all the tests here
    # currently do this.
    matrix_bot = menuai.data[DOMAIN]

    for room_id in TEST_JOINABLE_ROOMS:
        assert f"Joined or already in room '{room_id}'" in caplog.messages

    # Joining a disallowed room should not raise an exception.
    matrix_bot._listening_rooms = {TEST_BAD_ROOM: TEST_BAD_ROOM}
    await matrix_bot._join_rooms()
    assert (
        f"Could not join room '{TEST_BAD_ROOM}': JoinError: Not allowed to join this room."
        in caplog.messages
    )


async def test_resolve_aliases(menuai: menuai, matrix_bot: MatrixBot) -> None:
    """Test resolving configured room aliases into room ids."""

    await menuai.async_start()
    assert matrix_bot._listening_rooms == TEST_JOINABLE_ROOMS
