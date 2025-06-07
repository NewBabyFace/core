"""The tests for the person component."""

import logging
from typing import Any

import pytest

from menuai.components import person
from menuai.components.person import DOMAIN
from menuai.core import menuai
from menuai.helpers import collection
from menuai.setup import async_setup_component

from tests.common import MockUser

DEVICE_TRACKER = "device_tracker.test_tracker"
DEVICE_TRACKER_2 = "device_tracker.test_tracker_2"


@pytest.fixture
def storage_collection(menuai: menuai) -> person.PersonStorageCollection:
    """Return an empty storage collection."""
    id_manager = collection.IDManager()
    return person.PersonStorageCollection(
        person.PersonStore(menuai, person.STORAGE_VERSION, person.STORAGE_KEY),
        id_manager,
        collection.YamlCollection(
            logging.getLogger(f"{person.__name__}.yaml_collection"), id_manager
        ),
    )


@pytest.fixture
async def storage_setup(
    menuai: menuai, menuai_storage: dict[str, Any], menuai_admin_user: MockUser
) -> None:
    """Storage setup."""
    menuai_storage[DOMAIN] = {
        "key": DOMAIN,
        "version": 1,
        "data": {
            "persons": [
                {
                    "id": "1234",
                    "name": "tracked person",
                    "user_id": menuai_admin_user.id,
                    "device_trackers": [DEVICE_TRACKER],
                }
            ]
        },
    }
    assert await async_setup_component(menuai, DOMAIN, {})
