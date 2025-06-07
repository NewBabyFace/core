"""Define tests for the GIOS config flow."""

import json
from unittest.mock import patch

from gios import ApiError

from menuai.components.gios import config_flow
from menuai.components.gios.const import CONF_STATION_ID, DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_NAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import STATIONS

from tests.common import async_load_fixture

CONFIG = {
    CONF_NAME: "Foo",
    CONF_STATION_ID: "123",
}


async def test_show_form(menuai: menuai) -> None:
    """Test that the form is served with no input."""
    with patch(
        "menuai.components.gios.coordinator.Gios._get_stations",
        return_value=STATIONS,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_form_with_api_error(menuai: menuai) -> None:
    """Test the form is aborted because of API error."""
    with patch(
        "menuai.components.gios.coordinator.Gios._get_stations",
        side_effect=ApiError("error"),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )

    assert result["type"] is FlowResultType.ABORT


async def test_invalid_sensor_data(menuai: menuai) -> None:
    """Test that errors are shown when sensor data is invalid."""
    with (
        patch(
            "menuai.components.gios.coordinator.Gios._get_stations",
            return_value=STATIONS,
        ),
        patch(
            "menuai.components.gios.coordinator.Gios._get_station",
            return_value=json.loads(
                await async_load_fixture(menuai, "station.json", DOMAIN)
            ),
        ),
        patch(
            "menuai.components.gios.coordinator.Gios._get_sensor",
            return_value={},
        ),
    ):
        flow = config_flow.GiosFlowHandler()
        flow.menuai = menuai
        flow.context = {}

        result = await flow.async_step_user(user_input=CONFIG)

        assert result["errors"] == {CONF_STATION_ID: "invalid_sensors_data"}


async def test_cannot_connect(menuai: menuai) -> None:
    """Test that errors are shown when cannot connect to GIOS server."""
    with (
        patch(
            "menuai.components.gios.coordinator.Gios._get_stations",
            return_value=STATIONS,
        ),
        patch(
            "menuai.components.gios.coordinator.Gios._async_get",
            side_effect=ApiError("error"),
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], CONFIG
        )
        await menuai.async_block_till_done()

    assert result["errors"] == {"base": "cannot_connect"}


async def test_create_entry(menuai: menuai) -> None:
    """Test that the user step works."""
    with (
        patch(
            "menuai.components.gios.coordinator.Gios._get_stations",
            return_value=STATIONS,
        ),
        patch(
            "menuai.components.gios.coordinator.Gios._get_station",
            return_value=json.loads(
                await async_load_fixture(menuai, "station.json", DOMAIN)
            ),
        ),
        patch(
            "menuai.components.gios.coordinator.Gios._get_all_sensors",
            return_value=json.loads(
                await async_load_fixture(menuai, "sensors.json", DOMAIN)
            ),
        ),
        patch(
            "menuai.components.gios.coordinator.Gios._get_indexes",
            return_value=json.loads(
                await async_load_fixture(menuai, "indexes.json", DOMAIN)
            ),
        ),
    ):
        flow = config_flow.GiosFlowHandler()
        flow.menuai = menuai
        flow.context = {}

        result = await flow.async_step_user(user_input=CONFIG)

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == "Test Name 1"
        assert result["data"][CONF_STATION_ID] == CONFIG[CONF_STATION_ID]

        assert flow.context["unique_id"] == "123"
