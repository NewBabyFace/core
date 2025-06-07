"""Tests for the TotalConnect buttons."""

from unittest.mock import patch

import pytest
from syrupy.assertion import SnapshotAssertion
from total_connect_client.exceptions import FailedToBypassZone

from menuai.components.button import DOMAIN as BUTTON, SERVICE_PRESS
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .common import setup_platform

from tests.common import snapshot_platform

ZONE_BYPASS_ID = "button.security_bypass"
PANEL_CLEAR_ID = "button.test_clear_bypass"
PANEL_BYPASS_ID = "button.test_bypass_all"


async def test_entity_registry(
    menuai: menuai, entity_registry: er.EntityRegistry, snapshot: SnapshotAssertion
) -> None:
    """Test the button is registered in entity registry."""
    entry = await setup_platform(menuai, BUTTON)

    await snapshot_platform(menuai, entity_registry, snapshot, entry.entry_id)


@pytest.mark.parametrize(
    ("entity_id", "tcc_request"),
    [
        (ZONE_BYPASS_ID, "total_connect_client.zone.TotalConnectZone.bypass"),
        (
            PANEL_BYPASS_ID,
            "total_connect_client.location.TotalConnectLocation.zone_bypass_all",
        ),
    ],
)
async def test_bypass_button(
    menuai: menuai, entity_id: str, tcc_request: str
) -> None:
    """Test pushing a bypass button."""
    responses = [FailedToBypassZone, None]
    await setup_platform(menuai, BUTTON)
    with patch(tcc_request, side_effect=responses) as mock_request:
        # try to bypass, but fails
        with pytest.raises(FailedToBypassZone):
            await menuai.services.async_call(
                domain=BUTTON,
                service=SERVICE_PRESS,
                service_data={ATTR_ENTITY_ID: entity_id},
                blocking=True,
            )
        assert mock_request.call_count == 1

        # try to bypass, works this time
        await menuai.services.async_call(
            domain=BUTTON,
            service=SERVICE_PRESS,
            service_data={ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )
        assert mock_request.call_count == 2


async def test_clear_button(menuai: menuai) -> None:
    """Test pushing the clear bypass button."""
    data = {ATTR_ENTITY_ID: PANEL_CLEAR_ID}
    await setup_platform(menuai, BUTTON)
    TOTALCONNECT_REQUEST = (
        "total_connect_client.location.TotalConnectLocation.clear_bypass"
    )

    with patch(TOTALCONNECT_REQUEST) as mock_request:
        await menuai.services.async_call(
            domain=BUTTON,
            service=SERVICE_PRESS,
            service_data=data,
            blocking=True,
        )
        assert mock_request.call_count == 1
