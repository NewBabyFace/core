"""Tests for switchbot vacuum."""

from collections.abc import Callable
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from menuai.components.bluetooth import BluetoothServiceInfoBleak
from menuai.components.vacuum import (
    DOMAIN as VACUUM_DOMAIN,
    SERVICE_RETURN_TO_BASE,
    SERVICE_START,
)
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai

from . import (
    K10_POR_COMBO_VACUUM_SERVICE_INFO,
    K10_PRO_VACUUM_SERVICE_INFO,
    K10_VACUUM_SERVICE_INFO,
    K20_VACUUM_SERVICE_INFO,
    S10_VACUUM_SERVICE_INFO,
)

from tests.common import MockConfigEntry
from tests.components.bluetooth import inject_bluetooth_service_info


@pytest.mark.parametrize(
    ("sensor_type", "service_info"),
    [
        ("k20_vacuum", K20_VACUUM_SERVICE_INFO),
        ("s10_vacuum", S10_VACUUM_SERVICE_INFO),
        ("k10_pro_combo_vacumm", K10_POR_COMBO_VACUUM_SERVICE_INFO),
        ("k10_vacuum", K10_VACUUM_SERVICE_INFO),
        ("k10_pro_vacuum", K10_PRO_VACUUM_SERVICE_INFO),
    ],
)
@pytest.mark.parametrize(
    ("service", "mock_method"),
    [(SERVICE_START, "clean_up"), (SERVICE_RETURN_TO_BASE, "return_to_dock")],
)
async def test_vacuum_controlling(
    menuai: menuai,
    mock_entry_factory: Callable[[str], MockConfigEntry],
    sensor_type: str,
    service: str,
    mock_method: str,
    service_info: BluetoothServiceInfoBleak,
) -> None:
    """Test switchbot vacuum controlling."""

    inject_bluetooth_service_info(menuai, service_info)

    entry = mock_entry_factory(sensor_type)
    entry.add_to_menuai(menuai)

    mocked_instance = AsyncMock(return_value=True)

    with patch.multiple(
        "menuai.components.switchbot.vacuum.switchbot.SwitchbotVacuum",
        update=MagicMock(return_value=None),
        **{mock_method: mocked_instance},
    ):
        assert await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

        entity_id = "vacuum.test_name"

        await menuai.services.async_call(
            VACUUM_DOMAIN,
            service,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )

        mocked_instance.assert_awaited_once()
