"""The tests for the command line notification platform."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch

import pytest

from menuai import setup
from menuai.components.command_line import DOMAIN
from menuai.components.notify import DOMAIN as NOTIFY_DOMAIN
from menuai.core import menuai


async def test_setup_platform_yaml(menuai: menuai) -> None:
    """Test setting up the platform with platform yaml."""
    await setup.async_setup_component(
        menuai,
        "notify",
        {
            "notify": {
                "platform": "command_line",
                "command": "echo 1",
                "payload_on": "1",
                "payload_off": "0",
            }
        },
    )
    await menuai.async_block_till_done()
    assert len(menuai.states.async_all()) == 0


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "notify": {
                        "command": "exit 0",
                        "name": "Test2",
                    }
                }
            ]
        }
    ],
)
async def test_setup_integration_yaml(
    menuai: menuai, load_yaml_integration: None
) -> None:
    """Test sensor setup."""
    assert menuai.services.has_service(NOTIFY_DOMAIN, "test2")


async def test_bad_config(menuai: menuai) -> None:
    """Test set up the platform with bad/missing configuration."""
    assert await setup.async_setup_component(
        menuai,
        NOTIFY_DOMAIN,
        {
            NOTIFY_DOMAIN: [
                {"platform": "command_line"},
            ]
        },
    )
    await menuai.async_block_till_done()
    assert not menuai.services.has_service(NOTIFY_DOMAIN, "test")


async def test_command_line_output(menuai: menuai) -> None:
    """Test the command line output."""
    with tempfile.TemporaryDirectory() as tempdirname:
        filename = os.path.join(tempdirname, "message.txt")
        message = "one, two, testing, testing"
        await setup.async_setup_component(
            menuai,
            DOMAIN,
            {
                "command_line": [
                    {
                        "notify": {
                            "command": f"cat > {filename}",
                            "name": "Test3",
                        }
                    }
                ]
            },
        )
        await menuai.async_block_till_done()

        assert menuai.services.has_service(NOTIFY_DOMAIN, "test3")

        await menuai.services.async_call(
            NOTIFY_DOMAIN, "test3", {"message": message}, blocking=True
        )
        assert message == await menuai.async_add_executor_job(Path(filename).read_text)


async def test_command_line_output_single_command(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test the command line output."""

    await setup.async_setup_component(
        menuai,
        DOMAIN,
        {
            "command_line": [
                {
                    "notify": {
                        "command": "echo",
                        "name": "Test3",
                    }
                }
            ]
        },
    )
    await menuai.async_block_till_done()

    assert menuai.services.has_service(NOTIFY_DOMAIN, "test3")

    await menuai.services.async_call(
        NOTIFY_DOMAIN, "test3", {"message": "test message"}, blocking=True
    )
    assert "Running command: echo, with message: test message" in caplog.text


async def test_command_template(menuai: menuai) -> None:
    """Test the command line output using template as command."""

    with tempfile.TemporaryDirectory() as tempdirname:
        filename = os.path.join(tempdirname, "message.txt")
        message = "one, two, testing, testing"
        menuai.states.async_set("sensor.test_state", filename)
        await setup.async_setup_component(
            menuai,
            DOMAIN,
            {
                "command_line": [
                    {
                        "notify": {
                            "command": "cat > {{ states.sensor.test_state.state }}",
                            "name": "Test3",
                        }
                    }
                ]
            },
        )
        await menuai.async_block_till_done()

        assert menuai.services.has_service(NOTIFY_DOMAIN, "test3")

        await menuai.services.async_call(
            NOTIFY_DOMAIN, "test3", {"message": message}, blocking=True
        )
        assert message == await menuai.async_add_executor_job(Path(filename).read_text)


async def test_command_incorrect_template(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test the command line output using template as command which isn't working."""

    message = "one, two, testing, testing"
    await setup.async_setup_component(
        menuai,
        DOMAIN,
        {
            "command_line": [
                {
                    "notify": {
                        "command": "cat > {{ this template doesn't parse ",
                        "name": "Test3",
                    }
                }
            ]
        },
    )
    await menuai.async_block_till_done()

    assert menuai.services.has_service(NOTIFY_DOMAIN, "test3")

    await menuai.services.async_call(
        NOTIFY_DOMAIN, "test3", {"message": message}, blocking=True
    )

    assert (
        "Error rendering command template: TemplateSyntaxError: expected token"
        in caplog.text
    )


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "notify": {
                        "command": "exit 1",
                        "name": "Test4",
                    }
                }
            ]
        }
    ],
)
async def test_error_for_none_zero_exit_code(
    caplog: pytest.LogCaptureFixture, menuai: menuai, load_yaml_integration: None
) -> None:
    """Test if an error is logged for non zero exit codes."""

    await menuai.services.async_call(
        NOTIFY_DOMAIN, "test4", {"message": "error"}, blocking=True
    )
    assert "Command failed" in caplog.text
    assert "return code 1" in caplog.text


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "notify": {
                        "command": "sleep 10000",
                        "command_timeout": 0.0000001,
                        "name": "Test5",
                    }
                }
            ]
        }
    ],
)
async def test_timeout(
    caplog: pytest.LogCaptureFixture, menuai: menuai, load_yaml_integration: None
) -> None:
    """Test blocking is not forever."""
    await menuai.services.async_call(
        NOTIFY_DOMAIN, "test5", {"message": "error"}, blocking=True
    )
    assert "Timeout" in caplog.text


@pytest.mark.parametrize(
    "get_config",
    [
        {
            "command_line": [
                {
                    "notify": {
                        "command": "exit 0",
                        "name": "Test6",
                    }
                }
            ]
        }
    ],
)
async def test_subprocess_exceptions(
    caplog: pytest.LogCaptureFixture, menuai: menuai, load_yaml_integration: None
) -> None:
    """Test that notify subprocess exceptions are handled correctly."""

    with patch(
        "menuai.components.command_line.notify.subprocess.Popen"
    ) as check_output:
        check_output.return_value.__enter__ = check_output
        check_output.return_value.communicate.side_effect = [
            subprocess.TimeoutExpired("cmd", 10),
            None,
            subprocess.SubprocessError(),
        ]

        await menuai.services.async_call(
            NOTIFY_DOMAIN, "test6", {"message": "error"}, blocking=True
        )
        assert check_output.call_count == 2
        assert "Timeout for command" in caplog.text

        await menuai.services.async_call(
            NOTIFY_DOMAIN, "test6", {"message": "error"}, blocking=True
        )
        assert check_output.call_count == 4
        assert "Error trying to exec command" in caplog.text
