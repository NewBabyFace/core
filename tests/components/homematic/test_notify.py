"""The tests for the Homematic notification platform."""

from menuai.components.notify import DOMAIN as NOTIFY_DOMAIN
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import assert_setup_component


async def test_setup_full(menuai: menuai) -> None:
    """Test valid configuration."""
    await async_setup_component(
        menuai,
        "homematic",
        {"homematic": {"hosts": {"ccu2": {"host": "127.0.0.1"}}}},
    )
    with assert_setup_component(1, domain="notify") as handle_config:
        assert await async_setup_component(
            menuai,
            "notify",
            {
                "notify": {
                    "name": "test",
                    "platform": "homematic",
                    "address": "NEQXXXXXXX",
                    "channel": 2,
                    "param": "SUBMIT",
                    "value": "1,1,108000,2",
                    "interface": "my-interface",
                }
            },
        )
    assert handle_config[NOTIFY_DOMAIN]


async def test_setup_without_optional(menuai: menuai) -> None:
    """Test valid configuration without optional."""
    await async_setup_component(
        menuai,
        "homematic",
        {"homematic": {"hosts": {"ccu2": {"host": "127.0.0.1"}}}},
    )
    with assert_setup_component(1, domain="notify") as handle_config:
        assert await async_setup_component(
            menuai,
            "notify",
            {
                "notify": {
                    "name": "test",
                    "platform": "homematic",
                    "address": "NEQXXXXXXX",
                    "channel": 2,
                    "param": "SUBMIT",
                    "value": "1,1,108000,2",
                }
            },
        )
    assert handle_config[NOTIFY_DOMAIN]


async def test_bad_config(menuai: menuai) -> None:
    """Test invalid configuration."""
    config = {NOTIFY_DOMAIN: {"name": "test", "platform": "homematic"}}
    with assert_setup_component(0, domain="notify") as handle_config:
        assert await async_setup_component(menuai, NOTIFY_DOMAIN, config)
    assert not handle_config[NOTIFY_DOMAIN]
