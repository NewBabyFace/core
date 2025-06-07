"""Configure tests for the Dremel 3D Printer integration."""

from http import HTTPStatus
from unittest.mock import patch

import pytest
import requests_mock

from menuai.components.dremel_3d_printer.const import DOMAIN
from menuai.const import CONF_HOST
from menuai.core import menuai

from tests.common import MockConfigEntry, load_fixture

HOST = "1.2.3.4"
CONF_DATA = {CONF_HOST: HOST}


def create_entry(menuai: menuai) -> MockConfigEntry:
    """Create fixture for adding config entry in MenuAI."""
    entry = MockConfigEntry(domain=DOMAIN, data=CONF_DATA, unique_id="123456789")
    entry.add_to_menuai(menuai)
    return entry


@pytest.fixture
def config_entry(menuai: menuai) -> MockConfigEntry:
    """Add config entry in MenuAI."""
    return create_entry(menuai)


@pytest.fixture
def connection() -> None:
    """Mock Dremel 3D Printer connection."""
    with requests_mock.Mocker() as mock:
        mock.post(
            f"http://{HOST}/command",
            response_list=[
                {"text": load_fixture("dremel_3d_printer/command_1.json")},
                {"text": load_fixture("dremel_3d_printer/command_2.json")},
                {"text": load_fixture("dremel_3d_printer/command_1.json")},
                {"text": load_fixture("dremel_3d_printer/command_2.json")},
            ],
        )

        mock.post(
            f"https://{HOST}:11134/getHomeMessage",
            text=load_fixture("dremel_3d_printer/get_home_message.json"),
            status_code=HTTPStatus.OK,
        )
        yield


def patch_async_setup_entry():
    """Patch the async entry setup of Dremel 3D Printer."""
    return patch(
        "menuai.components.dremel_3d_printer.async_setup_entry",
        return_value=True,
    )
