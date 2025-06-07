"""Test Wallbox Select component."""

from unittest.mock import Mock, patch

import pytest

from menuai.components.select import (
    ATTR_OPTION,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from menuai.components.wallbox.const import CHARGER_STATUS_ID_KEY, EcoSmartMode
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai, menuaiError

from . import (
    authorisation_response,
    http_404_error,
    setup_integration_select,
    test_response,
    test_response_eco_mode,
    test_response_full_solar,
    test_response_no_power_boost,
)
from .const import MOCK_SELECT_ENTITY_ID

from tests.common import MockConfigEntry

TEST_OPTIONS = [
    (EcoSmartMode.OFF, test_response),
    (EcoSmartMode.ECO_MODE, test_response_eco_mode),
    (EcoSmartMode.FULL_SOLAR, test_response_full_solar),
]


@pytest.fixture
def mock_authenticate():
    """Fixture to patch Wallbox methods."""
    with patch(
        "menuai.components.wallbox.Wallbox.authenticate",
        new=Mock(return_value=authorisation_response),
    ):
        yield


@pytest.mark.parametrize(("mode", "response"), TEST_OPTIONS)
async def test_wallbox_select_solar_charging_class(
    menuai: menuai, entry: MockConfigEntry, mode, response, mock_authenticate
) -> None:
    """Test wallbox select class."""

    with (
        patch(
            "menuai.components.wallbox.Wallbox.enableEcoSmart",
            new=Mock(return_value={CHARGER_STATUS_ID_KEY: 193}),
        ),
        patch(
            "menuai.components.wallbox.Wallbox.disableEcoSmart",
            new=Mock(return_value={CHARGER_STATUS_ID_KEY: 193}),
        ),
    ):
        await setup_integration_select(menuai, entry, response)

        await menuai.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {
                ATTR_ENTITY_ID: MOCK_SELECT_ENTITY_ID,
                ATTR_OPTION: mode,
            },
            blocking=True,
        )

        state = menuai.states.get(MOCK_SELECT_ENTITY_ID)
        assert state.state == mode


async def test_wallbox_select_no_power_boost_class(
    menuai: menuai, entry: MockConfigEntry
) -> None:
    """Test wallbox select class."""

    await setup_integration_select(menuai, entry, test_response_no_power_boost)

    state = menuai.states.get(MOCK_SELECT_ENTITY_ID)
    assert state is None


@pytest.mark.parametrize(("mode", "response"), TEST_OPTIONS)
@pytest.mark.parametrize("error", [http_404_error, ConnectionError])
async def test_wallbox_select_class_error(
    menuai: menuai,
    entry: MockConfigEntry,
    mode,
    response,
    error,
    mock_authenticate,
) -> None:
    """Test wallbox select class connection error."""

    await setup_integration_select(menuai, entry, response)

    with (
        patch(
            "menuai.components.wallbox.Wallbox.disableEcoSmart",
            new=Mock(side_effect=error),
        ),
        patch(
            "menuai.components.wallbox.Wallbox.enableEcoSmart",
            new=Mock(side_effect=error),
        ),
        pytest.raises(menuaiError, match="Error communicating with Wallbox API"),
    ):
        await menuai.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {
                ATTR_ENTITY_ID: MOCK_SELECT_ENTITY_ID,
                ATTR_OPTION: mode,
            },
            blocking=True,
        )
