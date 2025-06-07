"""Test the wmspro button support."""

from unittest.mock import AsyncMock, patch

from syrupy.assertion import SnapshotAssertion

from menuai.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai

from . import setup_config_entry

from tests.common import MockConfigEntry


async def test_button_update(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_hub_ping: AsyncMock,
    mock_hub_configuration_prod_awning_dimmer: AsyncMock,
    mock_hub_status_prod_awning: AsyncMock,
    mock_action_call: AsyncMock,
    snapshot: SnapshotAssertion,
) -> None:
    """Test that a button entity is created and updated correctly."""
    assert await setup_config_entry(menuai, mock_config_entry)
    assert len(mock_hub_ping.mock_calls) == 1
    assert len(mock_hub_configuration_prod_awning_dimmer.mock_calls) == 1
    assert len(mock_hub_status_prod_awning.mock_calls) == 2

    entity = menuai.states.get("button.markise_identify")
    assert entity is not None
    assert entity == snapshot


async def test_button_press(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_hub_ping: AsyncMock,
    mock_hub_configuration_prod_awning_dimmer: AsyncMock,
    mock_hub_status_prod_awning: AsyncMock,
    mock_action_call: AsyncMock,
) -> None:
    """Test that a button entity is pressed correctly."""

    assert await setup_config_entry(menuai, mock_config_entry)

    with patch(
        "wmspro.destination.Destination.refresh",
        return_value=True,
    ):
        before = len(mock_hub_status_prod_awning.mock_calls)
        entity = menuai.states.get("button.markise_identify")
        before_state = entity.state

        await menuai.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: entity.entity_id},
            blocking=True,
        )

        entity = menuai.states.get("button.markise_identify")
        assert entity is not None
        assert entity.state != before_state
        assert len(mock_hub_status_prod_awning.mock_calls) == before
