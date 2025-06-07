"""The camera tests for the prosegur platform."""

import logging
from unittest.mock import AsyncMock

from pyprosegur.exceptions import ProsegurException
import pytest

from menuai.components import camera
from menuai.components.camera import Image
from menuai.components.prosegur.const import DOMAIN
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai
from menuai.exceptions import menuaiError


async def test_camera(menuai: menuai, init_integration) -> None:
    """Test prosegur get_image."""

    image = await camera.async_get_image(menuai, "camera.contract_1234abcd_test_cam")

    assert image == Image(content_type="image/jpeg", content=b"ABC")


async def test_camera_fail(
    menuai: menuai,
    init_integration,
    mock_install,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test prosegur get_image fails."""

    mock_install.get_image = AsyncMock(
        return_value=b"ABC", side_effect=ProsegurException()
    )

    with (
        caplog.at_level(logging.ERROR, logger="menuai.components.prosegur"),
        pytest.raises(menuaiError) as exc,
    ):
        await camera.async_get_image(menuai, "camera.contract_1234abcd_test_cam")

    assert "Unable to get image" in str(exc.value)

    assert "Image test_cam doesn't exist" in caplog.text


async def test_request_image(
    menuai: menuai, init_integration, mock_install
) -> None:
    """Test the camera request image service."""

    await menuai.services.async_call(
        DOMAIN,
        "request_image",
        {ATTR_ENTITY_ID: "camera.contract_1234abcd_test_cam"},
    )
    await menuai.async_block_till_done()

    assert mock_install.request_image.called


async def test_request_image_fail(
    menuai: menuai,
    init_integration,
    mock_install,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the camera request image service fails."""

    mock_install.request_image = AsyncMock(side_effect=ProsegurException())

    with caplog.at_level(logging.ERROR, logger="menuai.components.prosegur"):
        await menuai.services.async_call(
            DOMAIN,
            "request_image",
            {ATTR_ENTITY_ID: "camera.contract_1234abcd_test_cam"},
        )
        await menuai.async_block_till_done()

        assert mock_install.request_image.called

        assert "Could not request image from camera test_cam" in caplog.text
