"""The tests for the Datadog component."""

from unittest import mock
from unittest.mock import patch

from menuai.components import datadog
from menuai.const import EVENT_LOGBOOK_ENTRY, STATE_OFF, STATE_ON
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import assert_setup_component


async def test_invalid_config(menuai: menuai) -> None:
    """Test invalid configuration."""
    with assert_setup_component(0):
        assert not await async_setup_component(
            menuai, datadog.DOMAIN, {datadog.DOMAIN: {"host1": "host1"}}
        )


async def test_datadog_setup_full(menuai: menuai) -> None:
    """Test setup with all data."""
    config = {datadog.DOMAIN: {"host": "host", "port": 123, "rate": 1, "prefix": "foo"}}

    with (
        patch("menuai.components.datadog.initialize") as mock_init,
        patch("menuai.components.datadog.statsd"),
    ):
        assert await async_setup_component(menuai, datadog.DOMAIN, config)

        assert mock_init.call_count == 1
        assert mock_init.call_args == mock.call(statsd_host="host", statsd_port=123)


async def test_datadog_setup_defaults(menuai: menuai) -> None:
    """Test setup with defaults."""
    with (
        patch("menuai.components.datadog.initialize") as mock_init,
        patch("menuai.components.datadog.statsd"),
    ):
        assert await async_setup_component(
            menuai,
            datadog.DOMAIN,
            {
                datadog.DOMAIN: {
                    "host": "host",
                    "port": datadog.DEFAULT_PORT,
                    "prefix": datadog.DEFAULT_PREFIX,
                }
            },
        )

        assert mock_init.call_count == 1
        assert mock_init.call_args == mock.call(statsd_host="host", statsd_port=8125)


async def test_logbook_entry(menuai: menuai) -> None:
    """Test event listener."""
    with (
        patch("menuai.components.datadog.initialize"),
        patch("menuai.components.datadog.statsd") as mock_statsd,
    ):
        assert await async_setup_component(
            menuai,
            datadog.DOMAIN,
            {datadog.DOMAIN: {"host": "host", "rate": datadog.DEFAULT_RATE}},
        )

        event = {
            "domain": "automation",
            "entity_id": "sensor.foo.bar",
            "message": "foo bar biz",
            "name": "triggered something",
        }
        menuai.bus.async_fire(EVENT_LOGBOOK_ENTRY, event)
        await menuai.async_block_till_done()

        assert mock_statsd.event.call_count == 1
        assert mock_statsd.event.call_args == mock.call(
            title="MenuAI",
            text=f"%%% \n **{event['name']}** {event['message']} \n %%%",
            tags=["entity:sensor.foo.bar", "domain:automation"],
        )

        mock_statsd.event.reset_mock()


async def test_state_changed(menuai: menuai) -> None:
    """Test event listener."""
    with (
        patch("menuai.components.datadog.initialize"),
        patch("menuai.components.datadog.statsd") as mock_statsd,
    ):
        assert await async_setup_component(
            menuai,
            datadog.DOMAIN,
            {
                datadog.DOMAIN: {
                    "host": "host",
                    "prefix": "ha",
                    "rate": datadog.DEFAULT_RATE,
                }
            },
        )

        valid = {"1": 1, "1.0": 1.0, STATE_ON: 1, STATE_OFF: 0}

        attributes = {"elevation": 3.2, "temperature": 5.0, "up": True, "down": False}

        for in_, out in valid.items():
            state = mock.MagicMock(
                domain="sensor",
                entity_id="sensor.foobar",
                state=in_,
                attributes=attributes,
            )
            menuai.states.async_set(state.entity_id, state.state, state.attributes)
            await menuai.async_block_till_done()
            assert mock_statsd.gauge.call_count == 5

            for attribute, value in attributes.items():
                value = int(value) if isinstance(value, bool) else value
                mock_statsd.gauge.assert_has_calls(
                    [
                        mock.call(
                            f"ha.sensor.{attribute}",
                            value,
                            sample_rate=1,
                            tags=[f"entity:{state.entity_id}"],
                        )
                    ]
                )

            assert mock_statsd.gauge.call_args == mock.call(
                "ha.sensor",
                out,
                sample_rate=1,
                tags=[f"entity:{state.entity_id}"],
            )

            mock_statsd.gauge.reset_mock()

        for invalid in ("foo", "", object):
            menuai.states.async_set("domain.test", invalid, {})
            await menuai.async_block_till_done()
            assert not mock_statsd.gauge.called
