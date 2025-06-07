"""Test samsungtv diagnostics."""

from unittest.mock import Mock

import pytest
from samsungtvws.exceptions import HttpApiError
from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.components.samsungtv.const import DOMAIN
from menuai.core import menuai

from . import setup_samsungtv_entry
from .const import ENTRYDATA_ENCRYPTED_WEBSOCKET, ENTRYDATA_WEBSOCKET

from tests.common import async_load_json_object_fixture
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


@pytest.mark.usefixtures("remote_websocket", "rest_api")
async def test_entry_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test config entry diagnostics."""
    config_entry = await setup_samsungtv_entry(menuai, ENTRYDATA_WEBSOCKET)

    assert await get_diagnostics_for_config_entry(
        menuai, menuai_client, config_entry
    ) == snapshot(exclude=props("created_at", "modified_at"))


@pytest.mark.usefixtures("remote_encrypted_websocket")
async def test_entry_diagnostics_encrypted(
    menuai: menuai,
    rest_api: Mock,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test config entry diagnostics."""
    rest_api.rest_device_info.return_value = await async_load_json_object_fixture(
        menuai, "device_info_UE48JU6400.json", DOMAIN
    )
    config_entry = await setup_samsungtv_entry(menuai, ENTRYDATA_ENCRYPTED_WEBSOCKET)

    assert await get_diagnostics_for_config_entry(
        menuai, menuai_client, config_entry
    ) == snapshot(exclude=props("created_at", "modified_at"))


@pytest.mark.usefixtures("remote_encrypted_websocket")
async def test_entry_diagnostics_encrypte_offline(
    menuai: menuai,
    rest_api: Mock,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test config entry diagnostics."""
    rest_api.rest_device_info.side_effect = HttpApiError
    config_entry = await setup_samsungtv_entry(menuai, ENTRYDATA_ENCRYPTED_WEBSOCKET)

    assert await get_diagnostics_for_config_entry(
        menuai, menuai_client, config_entry
    ) == snapshot(exclude=props("created_at", "modified_at"))
