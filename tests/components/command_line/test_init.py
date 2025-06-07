"""Test Command line component setup process."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest

from menuai import config as menuai_config
from menuai.components.command_line.const import DOMAIN
from menuai.const import SERVICE_RELOAD, STATE_ON, STATE_OPEN
from menuai.core import menuai
from menuai.util import dt as dt_util

from tests.common import async_fire_time_changed, get_fixture_path


async def test_setup_config(menuai: menuai, load_yaml_integration: None) -> None:
    """Test setup from yaml."""

    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(minutes=10))
    await menuai.async_block_till_done(wait_background_tasks=True)

    state_binary_sensor = menuai.states.get("binary_sensor.test")
    state_sensor = menuai.states.get("sensor.test")
    state_cover = menuai.states.get("cover.test")
    state_switch = menuai.states.get("switch.test")

    assert state_binary_sensor.state == STATE_ON
    assert state_sensor.state == "5"
    assert state_cover.state == STATE_OPEN
    assert state_switch.state == STATE_ON


async def test_reload_service(
    menuai: menuai, load_yaml_integration: None, caplog: pytest.LogCaptureFixture
) -> None:
    """Test reload serviice."""

    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(minutes=10))
    await menuai.async_block_till_done()

    state_binary_sensor = menuai.states.get("binary_sensor.test")
    state_sensor = menuai.states.get("sensor.test")
    assert state_binary_sensor.state == STATE_ON
    assert state_sensor.state == "5"

    caplog.clear()

    yaml_path = get_fixture_path("configuration.yaml", "command_line")
    with patch.object(menuai_config, "YAML_CONFIG_FILE", yaml_path):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_RELOAD,
            {},
            blocking=True,
        )
        await menuai.async_block_till_done()

    assert "Loading config" in caplog.text

    state_binary_sensor = menuai.states.get("binary_sensor.test")
    state_sensor = menuai.states.get("sensor.test")
    assert state_binary_sensor.state == STATE_ON
    assert not state_sensor

    caplog.clear()

    yaml_path = get_fixture_path("configuration_empty.yaml", "command_line")
    with patch.object(menuai_config, "YAML_CONFIG_FILE", yaml_path):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_RELOAD,
            {},
            blocking=True,
        )
        await menuai.async_block_till_done()

    state_binary_sensor = menuai.states.get("binary_sensor.test")
    state_sensor = menuai.states.get("sensor.test")
    assert not state_binary_sensor
    assert not state_sensor

    assert "Loading config" not in caplog.text
