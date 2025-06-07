"""Test the HVV Departures config flow."""

import json
from unittest.mock import patch

from pygti.exceptions import CannotConnect, InvalidAuth

from menuai.components.hvv_departures.const import (
    CONF_FILTER,
    CONF_REAL_TIME,
    CONF_STATION,
    DOMAIN,
)
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_HOST, CONF_OFFSET, CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry, load_fixture

FIXTURE_INIT = json.loads(load_fixture("hvv_departures/init.json"))
FIXTURE_CHECK_NAME = json.loads(load_fixture("hvv_departures/check_name.json"))
FIXTURE_STATION_INFORMATION = json.loads(
    load_fixture("hvv_departures/station_information.json")
)
FIXTURE_CONFIG_ENTRY = json.loads(load_fixture("hvv_departures/config_entry.json"))
FIXTURE_OPTIONS = json.loads(load_fixture("hvv_departures/options.json"))
FIXTURE_DEPARTURE_LIST = json.loads(load_fixture("hvv_departures/departure_list.json"))


async def test_user_flow(menuai: menuai) -> None:
    """Test that config flow works."""

    with (
        patch(
            "menuai.components.hvv_departures.hub.GTI.init",
            return_value=FIXTURE_INIT,
        ),
        patch(
            "menuai.components.hvv_departures.hub.GTI.checkName",
            return_value=FIXTURE_CHECK_NAME,
        ),
        patch(
            "menuai.components.hvv_departures.hub.GTI.stationInformation",
            return_value=FIXTURE_STATION_INFORMATION,
        ),
        patch(
            "menuai.components.hvv_departures.async_setup_entry",
            return_value=True,
        ),
    ):
        # step: user

        result_user = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data={
                CONF_HOST: "api-test.geofox.de",
                CONF_USERNAME: "test-username",
                CONF_PASSWORD: "test-password",
            },
        )

        assert result_user["step_id"] == "station"

        # step: station
        result_station = await menuai.config_entries.flow.async_configure(
            result_user["flow_id"],
            {CONF_STATION: "Wartenau"},
        )

        assert result_station["step_id"] == "station_select"

        # step: station_select
        result_station_select = await menuai.config_entries.flow.async_configure(
            result_user["flow_id"],
            {CONF_STATION: "Wartenau"},
        )

        assert result_station_select["type"] is FlowResultType.CREATE_ENTRY
        assert result_station_select["title"] == "Wartenau"
        assert result_station_select["data"] == {
            CONF_HOST: "api-test.geofox.de",
            CONF_USERNAME: "test-username",
            CONF_PASSWORD: "test-password",
            CONF_STATION: {
                "name": "Wartenau",
                "city": "Hamburg",
                "combinedName": "Wartenau",
                "id": "Master:10901",
                "type": "STATION",
                "coordinate": {"x": 10.035515, "y": 53.56478},
                "serviceTypes": ["bus", "u"],
                "menuaitationInformation": True,
            },
        }


async def test_user_flow_no_results(menuai: menuai) -> None:
    """Test that config flow works when there are no results."""

    with (
        patch(
            "menuai.components.hvv_departures.hub.GTI.init",
            return_value=FIXTURE_INIT,
        ),
        patch(
            "menuai.components.hvv_departures.hub.GTI.checkName",
            return_value={"returnCode": "OK", "results": []},
        ),
        patch(
            "menuai.components.hvv_departures.async_setup_entry",
            return_value=True,
        ),
    ):
        # step: user

        result_user = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data={
                CONF_HOST: "api-test.geofox.de",
                CONF_USERNAME: "test-username",
                CONF_PASSWORD: "test-password",
            },
        )

        assert result_user["step_id"] == "station"

        # step: station
        result_station = await menuai.config_entries.flow.async_configure(
            result_user["flow_id"],
            {CONF_STATION: "non_existing_station"},
        )

        assert result_station["step_id"] == "station"
        assert result_station["errors"]["base"] == "no_results"


async def test_user_flow_invalid_auth(menuai: menuai) -> None:
    """Test that config flow handles invalid auth."""

    with patch(
        "menuai.components.hvv_departures.hub.GTI.init",
        side_effect=InvalidAuth(
            "ERROR_TEXT",
            "Bei der Verarbeitung der Anfrage ist ein technisches Problem aufgetreten.",  # codespell:ignore ist
            "Authentication failed!",
        ),
    ):
        # step: user
        result_user = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data={
                CONF_HOST: "api-test.geofox.de",
                CONF_USERNAME: "test-username",
                CONF_PASSWORD: "test-password",
            },
        )

        assert result_user["type"] is FlowResultType.FORM
        assert result_user["errors"] == {"base": "invalid_auth"}


async def test_user_flow_cannot_connect(menuai: menuai) -> None:
    """Test that config flow handles connection errors."""

    with patch(
        "menuai.components.hvv_departures.hub.GTI.init",
        side_effect=CannotConnect(),
    ):
        # step: user
        result_user = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data={
                CONF_HOST: "api-test.geofox.de",
                CONF_USERNAME: "test-username",
                CONF_PASSWORD: "test-password",
            },
        )

        assert result_user["type"] is FlowResultType.FORM
        assert result_user["errors"] == {"base": "cannot_connect"}


async def test_user_flow_station(menuai: menuai) -> None:
    """Test that config flow handles empty data on step station."""

    with (
        patch(
            "menuai.components.hvv_departures.hub.GTI.init",
            return_value=True,
        ),
        patch(
            "menuai.components.hvv_departures.hub.GTI.checkName",
            return_value={"returnCode": "OK", "results": []},
        ),
    ):
        # step: user

        result_user = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data={
                CONF_HOST: "api-test.geofox.de",
                CONF_USERNAME: "test-username",
                CONF_PASSWORD: "test-password",
            },
        )

        assert result_user["step_id"] == "station"

        # step: station
        result_station = await menuai.config_entries.flow.async_configure(
            result_user["flow_id"],
            None,
        )
        assert result_station["type"] is FlowResultType.FORM
        assert result_station["step_id"] == "station"


async def test_user_flow_station_select(menuai: menuai) -> None:
    """Test that config flow handles empty data on step station_select."""

    with (
        patch(
            "menuai.components.hvv_departures.hub.GTI.init",
            return_value=True,
        ),
        patch(
            "menuai.components.hvv_departures.hub.GTI.checkName",
            return_value=FIXTURE_CHECK_NAME,
        ),
    ):
        result_user = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data={
                CONF_HOST: "api-test.geofox.de",
                CONF_USERNAME: "test-username",
                CONF_PASSWORD: "test-password",
            },
        )

        result_station = await menuai.config_entries.flow.async_configure(
            result_user["flow_id"],
            {CONF_STATION: "Wartenau"},
        )

        # step: station_select
        result_station_select = await menuai.config_entries.flow.async_configure(
            result_station["flow_id"],
            None,
        )

        assert result_station_select["type"] is FlowResultType.FORM
        assert result_station_select["step_id"] == "station_select"


async def test_options_flow(menuai: menuai) -> None:
    """Test that options flow works."""

    config_entry = MockConfigEntry(
        version=1,
        domain=DOMAIN,
        title="Wartenau",
        data=FIXTURE_CONFIG_ENTRY,
        source=SOURCE_USER,
        options=FIXTURE_OPTIONS,
        unique_id="1234",
    )
    config_entry.add_to_menuai(menuai)

    with (
        patch("menuai.components.hvv_departures.PLATFORMS", new=[]),
        patch(
            "menuai.components.hvv_departures.hub.GTI.init",
            return_value=True,
        ),
        patch(
            "menuai.components.hvv_departures.hub.GTI.departureList",
            return_value=FIXTURE_DEPARTURE_LIST,
        ),
    ):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

        result = await menuai.config_entries.options.async_init(config_entry.entry_id)

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "init"

        result = await menuai.config_entries.options.async_configure(
            result["flow_id"],
            user_input={CONF_FILTER: ["0"], CONF_OFFSET: 15, CONF_REAL_TIME: False},
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert config_entry.options == {
            CONF_FILTER: [
                {
                    "serviceID": "HHA-U:U1_HHA-U",
                    "stationIDs": ["Master:10902"],
                    "label": "Fuhlsbüttel Nord / Ochsenzoll / Norderstedt Mitte / Kellinghusenstraße / Ohlsdorf / Garstedt",
                    "serviceName": "U1",
                }
            ],
            CONF_OFFSET: 15,
            CONF_REAL_TIME: False,
        }


async def test_options_flow_invalid_auth(menuai: menuai) -> None:
    """Test that options flow works."""

    config_entry = MockConfigEntry(
        version=1,
        domain=DOMAIN,
        title="Wartenau",
        data=FIXTURE_CONFIG_ENTRY,
        source=SOURCE_USER,
        options=FIXTURE_OPTIONS,
        unique_id="1234",
    )
    config_entry.add_to_menuai(menuai)

    with (
        patch("menuai.components.hvv_departures.PLATFORMS", new=[]),
        patch(
            "menuai.components.hvv_departures.hub.GTI.init", return_value=True
        ),
        patch(
            "menuai.components.hvv_departures.hub.GTI.departureList",
            return_value=FIXTURE_DEPARTURE_LIST,
        ),
    ):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    with patch(
        "menuai.components.hvv_departures.hub.GTI.departureList",
        side_effect=InvalidAuth(
            "ERROR_TEXT",
            "Bei der Verarbeitung der Anfrage ist ein technisches Problem aufgetreten.",  # codespell:ignore ist
            "Authentication failed!",
        ),
    ):
        result = await menuai.config_entries.options.async_init(config_entry.entry_id)

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "init"

        assert result["errors"] == {"base": "invalid_auth"}


async def test_options_flow_cannot_connect(menuai: menuai) -> None:
    """Test that options flow works."""

    config_entry = MockConfigEntry(
        version=1,
        domain=DOMAIN,
        title="Wartenau",
        data=FIXTURE_CONFIG_ENTRY,
        source=SOURCE_USER,
        options=FIXTURE_OPTIONS,
        unique_id="1234",
    )
    config_entry.add_to_menuai(menuai)

    with (
        patch("menuai.components.hvv_departures.PLATFORMS", new=[]),
        patch(
            "menuai.components.hvv_departures.hub.GTI.init", return_value=True
        ),
        patch(
            "menuai.components.hvv_departures.hub.GTI.departureList",
            return_value=FIXTURE_DEPARTURE_LIST,
        ),
    ):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    with patch(
        "menuai.components.hvv_departures.hub.GTI.departureList",
        side_effect=CannotConnect(),
    ):
        result = await menuai.config_entries.options.async_init(config_entry.entry_id)

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "init"

        assert result["errors"] == {"base": "cannot_connect"}
