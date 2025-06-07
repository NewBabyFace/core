"""Test the SFR Box buttons."""

from collections.abc import Generator
from unittest.mock import patch

import pytest
from sfrbox_api.exceptions import SFRBoxError
from syrupy.assertion import SnapshotAssertion

from menuai.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from menuai.config_entries import ConfigEntry
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import device_registry as dr, entity_registry as er

pytestmark = pytest.mark.usefixtures("system_get_info", "dsl_get_info", "wan_get_info")


@pytest.fixture(autouse=True)
def override_platforms() -> Generator[None]:
    """Override PLATFORMS_WITH_AUTH."""
    with (
        patch(
            "menuai.components.sfr_box.PLATFORMS_WITH_AUTH", [Platform.BUTTON]
        ),
        patch("menuai.components.sfr_box.coordinator.SFRBox.authenticate"),
    ):
        yield


async def test_buttons(
    menuai: menuai,
    config_entry_with_auth: ConfigEntry,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test for SFR Box buttons."""
    await menuai.config_entries.async_setup(config_entry_with_auth.entry_id)
    await menuai.async_block_till_done()

    # Ensure devices are correctly registered
    device_entries = dr.async_entries_for_config_entry(
        device_registry, config_entry_with_auth.entry_id
    )
    assert device_entries == snapshot

    # Ensure entities are correctly registered
    entity_entries = er.async_entries_for_config_entry(
        entity_registry, config_entry_with_auth.entry_id
    )
    assert entity_entries == snapshot

    # Ensure entity states are correct
    states = [menuai.states.get(ent.entity_id) for ent in entity_entries]
    assert states == snapshot


async def test_reboot(menuai: menuai, config_entry_with_auth: ConfigEntry) -> None:
    """Test for SFR Box reboot button."""
    await menuai.config_entries.async_setup(config_entry_with_auth.entry_id)
    await menuai.async_block_till_done()

    # Reboot success
    service_data = {ATTR_ENTITY_ID: "button.sfr_box_restart"}
    with patch(
        "menuai.components.sfr_box.button.SFRBox.system_reboot"
    ) as mock_action:
        await menuai.services.async_call(
            BUTTON_DOMAIN, SERVICE_PRESS, service_data=service_data, blocking=True
        )

    assert len(mock_action.mock_calls) == 1
    assert mock_action.mock_calls[0][1] == ()

    # Reboot failed
    service_data = {ATTR_ENTITY_ID: "button.sfr_box_restart"}
    with (
        patch(
            "menuai.components.sfr_box.button.SFRBox.system_reboot",
            side_effect=SFRBoxError,
        ) as mock_action,
        pytest.raises(menuaiError),
    ):
        await menuai.services.async_call(
            BUTTON_DOMAIN, SERVICE_PRESS, service_data=service_data, blocking=True
        )

    assert len(mock_action.mock_calls) == 1
    assert mock_action.mock_calls[0][1] == ()
