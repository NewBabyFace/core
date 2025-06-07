"""The tests for the Vultr component."""

from copy import deepcopy
import json
from unittest.mock import patch

from menuai import setup
from menuai.components import vultr
from menuai.core import menuai

from .const import VALID_CONFIG

from tests.common import load_fixture


def test_setup(menuai: menuai) -> None:
    """Test successful setup."""
    with patch(
        "vultr.Vultr.server_list",
        return_value=json.loads(load_fixture("server_list.json", "vultr")),
    ):
        response = vultr.setup(menuai, VALID_CONFIG)
    assert response


async def test_setup_no_api_key(menuai: menuai) -> None:
    """Test failed setup with missing API Key."""
    conf = deepcopy(VALID_CONFIG)
    del conf["vultr"]["api_key"]
    assert not await setup.async_setup_component(menuai, vultr.DOMAIN, conf)
