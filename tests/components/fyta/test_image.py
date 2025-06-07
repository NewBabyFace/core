"""Test the MenuAI fyta sensor module."""

from datetime import timedelta
from http import HTTPStatus
from unittest.mock import AsyncMock

from freezegun.api import FrozenDateTimeFactory
from fyta_cli.fyta_exceptions import FytaConnectionError, FytaPlantError
from fyta_cli.fyta_models import Plant
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.fyta.const import DOMAIN
from menuai.components.image import ImageEntity
from menuai.const import STATE_UNAVAILABLE, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_platform

from tests.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_load_json_object_fixture,
    snapshot_platform,
)
from tests.typing import ClientSessionGenerator


async def test_all_entities(
    menuai: menuai,
    mock_fyta_connector: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test all entities."""

    await setup_platform(menuai, mock_config_entry, [Platform.IMAGE])
    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)

    assert len(menuai.states.async_all("image")) == 4


@pytest.mark.parametrize(
    "exception",
    [
        FytaConnectionError,
        FytaPlantError,
    ],
)
async def test_connection_error(
    menuai: menuai,
    exception: Exception,
    mock_fyta_connector: AsyncMock,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test connection error."""
    await setup_platform(menuai, mock_config_entry, [Platform.IMAGE])

    mock_fyta_connector.update_all_plants.side_effect = exception

    freezer.tick(delta=timedelta(hours=12))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert menuai.states.get("image.gummibaum_plant_image").state == STATE_UNAVAILABLE
    assert menuai.states.get("image.gummibaum_user_image").state == STATE_UNAVAILABLE


async def test_add_remove_entities(
    menuai: menuai,
    mock_fyta_connector: AsyncMock,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test if entities are added and old are removed."""

    await setup_platform(menuai, mock_config_entry, [Platform.IMAGE])

    assert menuai.states.get("image.gummibaum_plant_image") is not None
    assert menuai.states.get("image.gummibaum_user_image") is not None

    plants: dict[int, Plant] = {
        0: Plant.from_dict(
            await async_load_json_object_fixture(menuai, "plant_status1.json", DOMAIN)
        ),
        2: Plant.from_dict(
            await async_load_json_object_fixture(menuai, "plant_status3.json", DOMAIN)
        ),
    }
    mock_fyta_connector.update_all_plants.return_value = plants
    mock_fyta_connector.plant_list = {
        0: "Kautschukbaum",
        2: "Tomatenpflanze",
    }

    freezer.tick(delta=timedelta(minutes=10))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert menuai.states.get("image.kakaobaum_plant_image") is None
    assert menuai.states.get("image.kakaobaum_user_image") is None
    assert menuai.states.get("image.tomatenpflanze_plant_image") is not None
    assert menuai.states.get("image.tomatenpflanze_user_image") is not None


async def test_update_image(
    menuai: menuai,
    mock_fyta_connector: AsyncMock,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test if entity picture is updated."""

    await setup_platform(menuai, mock_config_entry, [Platform.IMAGE])

    image_entity: ImageEntity = menuai.data["domain_entities"]["image"][
        "image.gummibaum_plant_image"
    ]
    image_state_1 = menuai.states.get("image.gummibaum_plant_image")

    assert image_entity.image_url == "http://www.plant_picture.com/picture"

    plants: dict[int, Plant] = {
        0: Plant.from_dict(
            await async_load_json_object_fixture(
                menuai, "plant_status1_update.json", DOMAIN
            )
        ),
        2: Plant.from_dict(
            await async_load_json_object_fixture(menuai, "plant_status3.json", DOMAIN)
        ),
    }
    mock_fyta_connector.update_all_plants.return_value = plants
    mock_fyta_connector.plant_list = {
        0: "Kautschukbaum",
        2: "Tomatenpflanze",
    }

    freezer.tick(delta=timedelta(minutes=10))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    image_state_2 = menuai.states.get("image.gummibaum_plant_image")

    assert image_entity.image_url == "http://www.plant_picture.com/picture1"
    assert image_state_1 != image_state_2


async def test_update_user_image_error(
    freezer: FrozenDateTimeFactory,
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    mock_fyta_connector: AsyncMock,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test error during user picture update."""

    mock_fyta_connector.get_plant_image.return_value = AsyncMock(return_value=None)

    await setup_platform(menuai, mock_config_entry, [Platform.IMAGE])

    mock_fyta_connector.get_plant_image.return_value = None

    freezer.tick(delta=timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    image_entity: ImageEntity = menuai.data["domain_entities"]["image"][
        "image.gummibaum_user_image"
    ]

    assert image_entity.image_url == "http://www.plant_picture.com/user_picture"
    assert image_entity._cached_image is None

    # Validate no image is available
    client = await menuai_client()
    resp = await client.get("/api/image_proxy/image.gummibaum_user_image?token=1")
    assert resp.status == 500


async def test_update_user_image(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    mock_fyta_connector: AsyncMock,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    snapshot: SnapshotAssertion,
) -> None:
    """Test if entity user picture is updated."""

    await setup_platform(menuai, mock_config_entry, [Platform.IMAGE])

    mock_fyta_connector.get_plant_image.return_value = (
        "image/png",
        bytes([100]),
    )

    freezer.tick(delta=timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    image_entity: ImageEntity = menuai.data["domain_entities"]["image"][
        "image.gummibaum_user_image"
    ]

    assert image_entity.image_url == "http://www.plant_picture.com/user_picture"
    image = image_entity._cached_image
    assert image == snapshot

    # Validate image
    client = await menuai_client()
    resp = await client.get("/api/image_proxy/image.gummibaum_user_image?token=1")
    assert resp.status == HTTPStatus.OK
    body = await resp.read()
    assert body == snapshot
