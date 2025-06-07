"""The test for the Yale smart living select."""

from __future__ import annotations

from unittest.mock import Mock

import pytest
from syrupy.assertion import SnapshotAssertion
from yalesmartalarmclient import YaleSmartAlarmData

from menuai.components.select import (
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from menuai.const import ATTR_ENTITY_ID, ATTR_OPTION, Platform
from menuai.core import menuai
from menuai.exceptions import ServiceValidationError
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry, snapshot_platform


@pytest.mark.parametrize(
    "load_platforms",
    [[Platform.SELECT]],
)
async def test_switch(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    load_config_entry: tuple[MockConfigEntry, Mock],
    get_data: YaleSmartAlarmData,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the Yale Smart Living volume select."""
    client = load_config_entry[1]

    await snapshot_platform(
        menuai, entity_registry, snapshot, load_config_entry[0].entry_id
    )

    await menuai.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {
            ATTR_ENTITY_ID: "select.device1_volume",
            ATTR_OPTION: "high",
        },
        blocking=True,
    )

    client.auth.post_authenticated.assert_called_once()
    client.auth.put_authenticated.assert_called_once()

    state = menuai.states.get("select.device1_volume")
    assert state.state == "high"

    with pytest.raises(ServiceValidationError):
        await menuai.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {
                ATTR_ENTITY_ID: "select.device1_volume",
                ATTR_OPTION: "not_exist",
            },
            blocking=True,
        )
