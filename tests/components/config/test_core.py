"""Test core config."""

from http import HTTPStatus
from unittest.mock import Mock, patch

import pytest

from menuai.components import config
from menuai.components.config import core
from menuai.components.websocket_api import TYPE_RESULT
from menuai.core import menuai
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util, location as location_util
from menuai.util.unit_system import US_CUSTOMARY_SYSTEM

from tests.common import MockUser
from tests.typing import (
    ClientSessionGenerator,
    MockHAClientWebSocket,
    WebSocketGenerator,
)


@pytest.fixture
async def client(
    menuai: menuai, menuai_ws_client: WebSocketGenerator
) -> MockHAClientWebSocket:
    """Fixture that can interact with the config manager API."""
    with patch.object(config, "SECTIONS", [core]):
        assert await async_setup_component(menuai, "config", {})
    return await menuai_ws_client(menuai)


async def test_validate_config_ok(
    menuai: menuai, menuai_client: ClientSessionGenerator
) -> None:
    """Test checking config."""
    with patch.object(config, "SECTIONS", [core]):
        await async_setup_component(menuai, "config", {})

    client = await menuai_client()

    no_error = Mock()
    no_error.errors = None
    no_error.error_str = ""
    no_error.warning_str = ""

    with patch(
        "menuai.components.config.core.check_config.async_check_ha_config_file",
        return_value=no_error,
    ):
        resp = await client.post("/api/config/core/check_config")

    assert resp.status == HTTPStatus.OK
    result = await resp.json()
    assert result["result"] == "valid"
    assert result["errors"] is None
    assert result["warnings"] is None

    error_warning = Mock()
    error_warning.errors = ["beer"]
    error_warning.error_str = "beer"
    error_warning.warning_str = "milk"

    with patch(
        "menuai.components.config.core.check_config.async_check_ha_config_file",
        return_value=error_warning,
    ):
        resp = await client.post("/api/config/core/check_config")

    assert resp.status == HTTPStatus.OK
    result = await resp.json()
    assert result["result"] == "invalid"
    assert result["errors"] == "beer"
    assert result["warnings"] == "milk"

    warning = Mock()
    warning.errors = None
    warning.error_str = ""
    warning.warning_str = "milk"

    with patch(
        "menuai.components.config.core.check_config.async_check_ha_config_file",
        return_value=warning,
    ):
        resp = await client.post("/api/config/core/check_config")

    assert resp.status == HTTPStatus.OK
    result = await resp.json()
    assert result["result"] == "valid"
    assert result["errors"] is None
    assert result["warnings"] == "milk"


async def test_validate_config_requires_admin(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    menuai_read_only_access_token: str,
) -> None:
    """Test checking configuration does not work as a normal user."""
    with patch.object(config, "SECTIONS", [core]):
        await async_setup_component(menuai, "config", {})

    client = await menuai_client(menuai_read_only_access_token)
    resp = await client.post("/api/config/core/check_config")

    assert resp.status == HTTPStatus.UNAUTHORIZED


async def test_websocket_core_update(menuai: menuai, client) -> None:
    """Test core config update websocket command."""
    assert menuai.config.latitude != 60
    assert menuai.config.longitude != 50
    assert menuai.config.elevation != 25
    assert menuai.config.location_name != "Huis"
    assert menuai.config.units is not US_CUSTOMARY_SYSTEM
    assert menuai.config.time_zone != "America/New_York"
    assert menuai.config.external_url != "https://www.example.com"
    assert menuai.config.internal_url != "http://example.com"
    assert menuai.config.currency == "EUR"
    assert menuai.config.country != "SE"
    assert menuai.config.language != "sv"
    assert menuai.config.radius != 150

    with (
        patch("menuai.util.dt.set_default_time_zone") as mock_set_tz,
        patch(
            "menuai.components.config.core.async_update_suggested_units"
        ) as mock_update_sensor_units,
    ):
        await client.send_json(
            {
                "id": 5,
                "type": "config/core/update",
                "latitude": 60,
                "longitude": 50,
                "elevation": 25,
                "location_name": "Huis",
                "unit_system": "imperial",
                "time_zone": "America/New_York",
                "external_url": "https://www.example.com",
                "internal_url": "http://example.local",
                "currency": "USD",
                "country": "SE",
                "language": "sv",
                "radius": 150,
            }
        )

        msg = await client.receive_json()

        mock_update_sensor_units.assert_not_called()

    assert msg["id"] == 5
    assert msg["type"] == TYPE_RESULT
    assert msg["success"]
    assert menuai.config.latitude == 60
    assert menuai.config.longitude == 50
    assert menuai.config.elevation == 25
    assert menuai.config.location_name == "Huis"
    assert menuai.config.units is US_CUSTOMARY_SYSTEM
    assert menuai.config.external_url == "https://www.example.com"
    assert menuai.config.internal_url == "http://example.local"
    assert menuai.config.currency == "USD"
    assert menuai.config.country == "SE"
    assert menuai.config.language == "sv"
    assert menuai.config.radius == 150

    assert len(mock_set_tz.mock_calls) == 1
    assert mock_set_tz.mock_calls[0][1][0] == dt_util.get_time_zone("America/New_York")

    with (
        patch("menuai.util.dt.set_default_time_zone") as mock_set_tz,
        patch(
            "menuai.components.config.core.async_update_suggested_units"
        ) as mock_update_sensor_units,
    ):
        await client.send_json(
            {
                "id": 6,
                "type": "config/core/update",
                "unit_system": "metric",
                "update_units": True,
            }
        )

        msg = await client.receive_json()

        mock_update_sensor_units.assert_called_once()


async def test_websocket_core_update_not_admin(
    menuai: menuai, menuai_ws_client: WebSocketGenerator, menuai_admin_user: MockUser
) -> None:
    """Test core config fails for non admin."""
    menuai_admin_user.groups = []
    with patch.object(config, "SECTIONS", [core]):
        await async_setup_component(menuai, "config", {})

    client = await menuai_ws_client(menuai)
    await client.send_json({"id": 6, "type": "config/core/update", "latitude": 23})

    msg = await client.receive_json()

    assert msg["id"] == 6
    assert msg["type"] == TYPE_RESULT
    assert not msg["success"]
    assert msg["error"]["code"] == "unauthorized"


async def test_websocket_bad_core_update(menuai: menuai, client) -> None:
    """Test core config update fails with bad parameters."""
    await client.send_json({"id": 7, "type": "config/core/update", "latituude": 23})

    msg = await client.receive_json()

    assert msg["id"] == 7
    assert msg["type"] == TYPE_RESULT
    assert not msg["success"]
    assert msg["error"]["code"] == "invalid_format"


async def test_detect_config(menuai: menuai, client) -> None:
    """Test detect config."""
    with patch(
        "menuai.util.location.async_detect_location_info",
        return_value=None,
    ):
        await client.send_json({"id": 1, "type": "config/core/detect"})

        msg = await client.receive_json()

    assert msg["success"] is True
    assert msg["result"] == {}


async def test_detect_config_fail(menuai: menuai, client) -> None:
    """Test detect config."""
    with patch(
        "menuai.util.location.async_detect_location_info",
        return_value=location_util.LocationInfo(
            ip=None,
            country_code=None,
            currency=None,
            region_code=None,
            region_name=None,
            city=None,
            zip_code=None,
            latitude=None,
            longitude=None,
            use_metric=True,
            time_zone="Europe/Amsterdam",
        ),
    ):
        await client.send_json({"id": 1, "type": "config/core/detect"})

        msg = await client.receive_json()

    assert msg["success"] is True
    assert msg["result"] == {"unit_system": "metric", "time_zone": "Europe/Amsterdam"}
