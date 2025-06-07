"""The tests for generic camera component."""

from datetime import timedelta
from http import HTTPStatus
import io

from menuai.core import menuai
from menuai.core_config import async_process_ha_core_config
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from tests.common import async_fire_time_changed
from tests.typing import ClientSessionGenerator


async def test_bad_posting(
    menuai: menuai, menuai_client_no_auth: ClientSessionGenerator
) -> None:
    """Test that posting to wrong api endpoint fails."""
    await async_process_ha_core_config(
        menuai,
        {"external_url": "http://example.com"},
    )

    await async_setup_component(
        menuai,
        "camera",
        {
            "camera": {
                "platform": "push",
                "name": "config_test",
                "webhook_id": "camera.config_test",
            }
        },
    )
    await menuai.async_block_till_done()
    assert menuai.states.get("camera.config_test") is not None

    client = await menuai_client_no_auth()

    # missing file
    async with client.post("/api/webhook/camera.config_test") as resp:
        assert resp.status == HTTPStatus.OK  # webhooks always return OK

    camera_state = menuai.states.get("camera.config_test")
    assert camera_state.state == "idle"  # no file supplied we are still idle


async def test_posting_url(
    menuai: menuai, menuai_client_no_auth: ClientSessionGenerator
) -> None:
    """Test that posting to api endpoint works."""
    await async_process_ha_core_config(
        menuai,
        {"external_url": "http://example.com"},
    )

    await async_setup_component(
        menuai,
        "camera",
        {
            "camera": {
                "platform": "push",
                "name": "config_test",
                "webhook_id": "camera.config_test",
            }
        },
    )
    await menuai.async_block_till_done()

    client = await menuai_client_no_auth()
    files = {"image": io.BytesIO(b"fake")}

    # initial state
    camera_state = menuai.states.get("camera.config_test")
    assert camera_state.state == "idle"

    # post image
    resp = await client.post("/api/webhook/camera.config_test", data=files)
    assert resp.status == HTTPStatus.OK

    # state recording
    camera_state = menuai.states.get("camera.config_test")
    assert camera_state.state == "recording"

    # await timeout
    shifted_time = dt_util.utcnow() + timedelta(seconds=15)
    async_fire_time_changed(menuai, shifted_time)
    await menuai.async_block_till_done()

    # back to initial state
    camera_state = menuai.states.get("camera.config_test")
    assert camera_state.state == "idle"
