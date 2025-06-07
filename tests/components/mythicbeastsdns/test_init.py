"""Test the Mythic Beasts DNS component."""

import logging
from unittest.mock import patch

from menuai.components import mythicbeastsdns
from menuai.core import menuai
from menuai.setup import async_setup_component

_LOGGER = logging.getLogger(__name__)


async def mbddns_update_mock(domain, password, host, ttl=60, session=None):
    """Mock out mythic beasts updater."""
    if password == "incorrect":
        _LOGGER.error("Updating Mythic Beasts failed: Not authenticated")
        return False
    if host[0] == "$":
        _LOGGER.error("Updating Mythic Beasts failed: Invalid Character")
        return False
    return True


@patch("mbddns.update", new=mbddns_update_mock)
async def test_update(menuai: menuai) -> None:
    """Run with correct values and check true is returned."""
    result = await async_setup_component(
        menuai,
        mythicbeastsdns.DOMAIN,
        {
            mythicbeastsdns.DOMAIN: {
                "domain": "example.org",
                "password": "correct",
                "host": "menuai",
            }
        },
    )
    assert result


@patch("mbddns.update", new=mbddns_update_mock)
async def test_update_fails_if_wrong_token(menuai: menuai) -> None:
    """Run with incorrect token and check false is returned."""
    result = await async_setup_component(
        menuai,
        mythicbeastsdns.DOMAIN,
        {
            mythicbeastsdns.DOMAIN: {
                "domain": "example.org",
                "password": "incorrect",
                "host": "menuai",
            }
        },
    )
    assert not result


@patch("mbddns.update", new=mbddns_update_mock)
async def test_update_fails_if_invalid_host(menuai: menuai) -> None:
    """Run with invalid characters in host and check false is returned."""
    result = await async_setup_component(
        menuai,
        mythicbeastsdns.DOMAIN,
        {
            mythicbeastsdns.DOMAIN: {
                "domain": "example.org",
                "password": "correct",
                "host": "$menuai",
            }
        },
    )
    assert not result
