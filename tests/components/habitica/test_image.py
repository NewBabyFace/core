"""Tests for the Habitica image platform."""

from collections.abc import Generator
from datetime import timedelta
from http import HTTPStatus
from io import BytesIO
import sys
from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory
from habiticalib import HabiticaUserResponse
import pytest
from syrupy.assertion import SnapshotAssertion
from syrupy.extensions.image import PNGImageSnapshotExtension

from menuai.components.habitica.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import Platform
from menuai.core import menuai

from tests.common import MockConfigEntry, async_fire_time_changed, async_load_fixture
from tests.typing import ClientSessionGenerator


@pytest.fixture(autouse=True)
def image_only() -> Generator[None]:
    """Enable only the image platform."""
    with patch(
        "menuai.components.habitica.PLATFORMS",
        [Platform.IMAGE],
    ):
        yield


@pytest.mark.skipif(
    sys.platform != "linux", reason="linux only"
)  # Pillow output on win/mac is different
async def test_image_platform(
    menuai: menuai,
    config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    menuai_client: ClientSessionGenerator,
    habitica: AsyncMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test image platform."""
    freezer.move_to("2024-09-20T22:00:00.000")
    with patch(
        "menuai.components.habitica.coordinator.BytesIO",
    ) as avatar:
        avatar.side_effect = [
            BytesIO(
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\xdac\xfc\xcf\xc0\xf0\x1f\x00\x05\x05\x02\x00_\xc8\xf1\xd2\x00\x00\x00\x00IEND\xaeB`\x82"
            ),
            BytesIO(
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\xdacd`\xf8\xff\x1f\x00\x03\x07\x02\x000&\xc7a\x00\x00\x00\x00IEND\xaeB`\x82"
            ),
        ]

        config_entry.add_to_menuai(menuai)
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

        assert config_entry.state is ConfigEntryState.LOADED

        assert (state := menuai.states.get("image.test_user_avatar"))
        assert state.state == "2024-09-20T22:00:00+00:00"

        access_token = state.attributes["access_token"]
        assert (
            state.attributes["entity_picture"]
            == f"/api/image_proxy/image.test_user_avatar?token={access_token}"
        )

        client = await menuai_client()
        resp = await client.get(state.attributes["entity_picture"])
        assert resp.status == HTTPStatus.OK

        assert (await resp.read()) == snapshot(
            extension_class=PNGImageSnapshotExtension
        )

        habitica.get_user.return_value = HabiticaUserResponse.from_json(
            await async_load_fixture(menuai, "rogue_fixture.json", DOMAIN)
        )

        freezer.tick(timedelta(seconds=60))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()

        assert (state := menuai.states.get("image.test_user_avatar"))
        assert state.state == "2024-09-20T22:01:00+00:00"

        resp = await client.get(state.attributes["entity_picture"])
        assert resp.status == HTTPStatus.OK

        assert (await resp.read()) == snapshot(
            extension_class=PNGImageSnapshotExtension
        )
