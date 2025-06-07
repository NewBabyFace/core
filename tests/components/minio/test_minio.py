"""Tests for Minio menuai related code."""

import asyncio
import json
from unittest.mock import MagicMock, call, patch

import pytest

from menuai.components.minio import (
    CONF_ACCESS_KEY,
    CONF_HOST,
    CONF_LISTEN,
    CONF_LISTEN_BUCKET,
    CONF_PORT,
    CONF_SECRET_KEY,
    CONF_SECURE,
    DOMAIN,
    QueueListener,
)
from menuai.core import menuai, callback
from menuai.setup import async_setup_component

from .common import TEST_EVENT


@pytest.fixture(name="minio_client")
def minio_client_fixture():
    """Patch Minio client."""
    with patch("menuai.components.minio.minio_helper.Minio") as minio_mock:
        minio_client_mock = minio_mock.return_value

        yield minio_client_mock


@pytest.fixture(name="minio_client_event")
def minio_client_event_fixture():
    """Patch helper function for minio notification stream."""
    with patch("menuai.components.minio.minio_helper.Minio") as minio_mock:
        minio_client_mock = minio_mock.return_value

        response_mock = MagicMock()
        stream_mock = MagicMock()

        stream_mock.__next__.side_effect = [
            "",
            "",
            bytearray(json.dumps(TEST_EVENT), "utf-8"),
        ]

        response_mock.stream.return_value = stream_mock
        minio_client_mock._url_open.return_value = response_mock

        yield minio_client_mock


async def test_minio_services(
    menuai: menuai, caplog: pytest.LogCaptureFixture, minio_client
) -> None:
    """Test Minio services."""
    menuai.config.allowlist_external_dirs = {"/test"}

    await async_setup_component(
        menuai,
        DOMAIN,
        {
            DOMAIN: {
                CONF_HOST: "localhost",
                CONF_PORT: "9000",
                CONF_ACCESS_KEY: "abcdef",
                CONF_SECRET_KEY: "0123456789",
                CONF_SECURE: "true",
            }
        },
    )

    await menuai.async_start()
    await menuai.async_block_till_done()

    # Call services
    await menuai.services.async_call(
        DOMAIN,
        "put",
        {"file_path": "/test/some_file", "key": "some_key", "bucket": "some_bucket"},
        blocking=True,
    )
    assert minio_client.fput_object.call_args == call(
        "some_bucket", "some_key", "/test/some_file"
    )
    minio_client.reset_mock()

    await menuai.services.async_call(
        DOMAIN,
        "get",
        {"file_path": "/test/some_file", "key": "some_key", "bucket": "some_bucket"},
        blocking=True,
    )
    assert minio_client.fget_object.call_args == call(
        "some_bucket", "some_key", "/test/some_file"
    )
    minio_client.reset_mock()

    await menuai.services.async_call(
        DOMAIN, "remove", {"key": "some_key", "bucket": "some_bucket"}, blocking=True
    )
    assert minio_client.remove_object.call_args == call("some_bucket", "some_key")
    minio_client.reset_mock()


async def test_minio_listen(
    menuai: menuai, caplog: pytest.LogCaptureFixture, minio_client_event
) -> None:
    """Test minio listen on notifications."""
    minio_client_event.presigned_get_object.return_value = "http://url"

    events = []

    @callback
    def event_callback(event):
        """Handle event callbback."""
        events.append(event)

    menuai.bus.async_listen("minio", event_callback)

    await async_setup_component(
        menuai,
        DOMAIN,
        {
            DOMAIN: {
                CONF_HOST: "localhost",
                CONF_PORT: "9000",
                CONF_ACCESS_KEY: "abcdef",
                CONF_SECRET_KEY: "0123456789",
                CONF_SECURE: "true",
                CONF_LISTEN: [{CONF_LISTEN_BUCKET: "test"}],
            }
        },
    )

    await menuai.async_start()
    await menuai.async_block_till_done()

    while not events:
        await asyncio.sleep(0)

    assert len(events) == 1
    event = events[0]

    assert event.event_type == DOMAIN
    assert event.data["event_name"] == "s3:ObjectCreated:Put"
    assert event.data["file_name"] == "5jJkTAo.jpg"
    assert event.data["bucket"] == "test"
    assert event.data["key"] == "5jJkTAo.jpg"
    assert event.data["presigned_url"] == "http://url"
    assert len(event.data["metadata"]) == 0


async def test_queue_listener() -> None:
    """Tests QueueListener firing events on MenuAI event bus."""
    menuai = MagicMock()

    queue_listener = QueueListener(menuai)
    queue_listener.start()

    queue_entry = {
        "event_name": "s3:ObjectCreated:Put",
        "bucket": "some_bucket",
        "key": "some_dir/some_file.jpg",
        "presigned_url": "http://host/url?signature=secret",
        "metadata": {},
    }

    queue_listener.queue.put(queue_entry)

    queue_listener.stop()

    call_domain, call_event = menuai.bus.fire.call_args[0]

    expected_event = {
        "event_name": "s3:ObjectCreated:Put",
        "file_name": "some_file.jpg",
        "bucket": "some_bucket",
        "key": "some_dir/some_file.jpg",
        "presigned_url": "http://host/url?signature=secret",
        "metadata": {},
    }

    assert call_domain == DOMAIN
    assert json.dumps(expected_event, sort_keys=True) == json.dumps(
        call_event, sort_keys=True
    )
