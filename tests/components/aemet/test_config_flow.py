"""Define tests for the AEMET OpenData config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

from aemet_opendata.exceptions import AuthError
from freezegun.api import FrozenDateTimeFactory
import pytest

from menuai.components.aemet.const import (
    CONF_RADAR_UPDATES,
    CONF_STATION_UPDATES,
    DOMAIN,
)
from menuai.config_entries import SOURCE_USER, ConfigEntryState
from menuai.const import CONF_API_KEY, CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .util import mock_api_call

from tests.common import MockConfigEntry

pytestmark = pytest.mark.usefixtures("mock_setup_entry")

CONFIG = {
    CONF_NAME: "aemet",
    CONF_API_KEY: "foo",
    CONF_LATITUDE: 40.30403754,
    CONF_LONGITUDE: -3.72935236,
}


async def test_form(menuai: menuai, mock_setup_entry: AsyncMock) -> None:
    """Test that the form is served with valid input."""

    with patch(
        "menuai.components.aemet.AEMET.api_call",
        side_effect=mock_api_call,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {}

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], CONFIG
        )

        await menuai.async_block_till_done()

        conf_entries = menuai.config_entries.async_entries(DOMAIN)
        entry = conf_entries[0]
        assert entry.state is ConfigEntryState.LOADED

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == CONFIG[CONF_NAME]
        assert result["data"][CONF_LATITUDE] == CONFIG[CONF_LATITUDE]
        assert result["data"][CONF_LONGITUDE] == CONFIG[CONF_LONGITUDE]
        assert result["data"][CONF_API_KEY] == CONFIG[CONF_API_KEY]

        assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("user_input", "expected"),
    [
        ({}, {CONF_RADAR_UPDATES: False, CONF_STATION_UPDATES: True}),
        (
            {CONF_RADAR_UPDATES: False, CONF_STATION_UPDATES: False},
            {CONF_RADAR_UPDATES: False, CONF_STATION_UPDATES: False},
        ),
    ],
)
async def test_form_options(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    user_input: dict[str, bool],
    expected: dict[str, bool],
) -> None:
    """Test the form options."""

    await menuai.config.async_set_time_zone("UTC")
    freezer.move_to("2021-01-09 12:00:00+00:00")
    with patch(
        "menuai.components.aemet.AEMET.api_call",
        side_effect=mock_api_call,
    ):
        entry = MockConfigEntry(
            domain=DOMAIN, unique_id="40.30403754--3.72935236", data=CONFIG
        )
        entry.add_to_menuai(menuai)

        assert await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

        assert entry.state is ConfigEntryState.LOADED

        result = await menuai.config_entries.options.async_init(entry.entry_id)

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "init"

        result = await menuai.config_entries.options.async_configure(
            result["flow_id"], user_input=user_input
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert entry.options == {
            CONF_RADAR_UPDATES: expected[CONF_RADAR_UPDATES],
            CONF_STATION_UPDATES: expected[CONF_STATION_UPDATES],
        }

        await menuai.async_block_till_done()

        assert entry.state is ConfigEntryState.LOADED


async def test_form_duplicated_id(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test setting up duplicated entry."""

    await menuai.config.async_set_time_zone("UTC")
    freezer.move_to("2021-01-09 12:00:00+00:00")
    with patch(
        "menuai.components.aemet.AEMET.api_call",
        side_effect=mock_api_call,
    ):
        entry = MockConfigEntry(
            domain=DOMAIN, unique_id="40.30403754--3.72935236", data=CONFIG
        )
        entry.add_to_menuai(menuai)

        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=CONFIG
        )

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"


async def test_form_auth_error(menuai: menuai) -> None:
    """Test setting up with api auth error."""
    mocked_aemet = MagicMock()
    mocked_aemet.select_coordinates.side_effect = AuthError

    with patch(
        "menuai.components.aemet.config_flow.AEMET",
        return_value=mocked_aemet,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=CONFIG
        )

        assert result["errors"] == {"base": "invalid_api_key"}
