"""Tests for the number platform."""

from unittest.mock import patch

import pytest

from menuai.components.number import (
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai
from menuai.exceptions import ServiceValidationError

from .common import ENTITY_HUMIDIFIER_MIST_LEVEL

from tests.common import MockConfigEntry


async def test_set_mist_level_bad_range(
    menuai: menuai, humidifier_config_entry: MockConfigEntry
) -> None:
    """Test set_mist_level invalid value."""
    with (
        pytest.raises(ServiceValidationError),
        patch(
            "pyvesync.vesyncfan.VeSyncHumid200300S.set_mist_level",
            return_value=True,
        ) as method_mock,
    ):
        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: ENTITY_HUMIDIFIER_MIST_LEVEL, ATTR_VALUE: "10"},
            blocking=True,
        )
    await menuai.async_block_till_done()
    method_mock.assert_not_called()


async def test_set_mist_level(
    menuai: menuai, humidifier_config_entry: MockConfigEntry
) -> None:
    """Test set_mist_level usage."""

    with patch(
        "pyvesync.vesyncfan.VeSyncHumid200300S.set_mist_level",
        return_value=True,
    ) as method_mock:
        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: ENTITY_HUMIDIFIER_MIST_LEVEL, ATTR_VALUE: "3"},
            blocking=True,
        )
    await menuai.async_block_till_done()
    method_mock.assert_called_once()


async def test_mist_level(
    menuai: menuai, humidifier_config_entry: MockConfigEntry
) -> None:
    """Test the state of mist_level number entity."""

    assert menuai.states.get(ENTITY_HUMIDIFIER_MIST_LEVEL).state == "6"
