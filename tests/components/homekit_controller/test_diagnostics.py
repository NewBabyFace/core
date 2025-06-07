"""Test homekit_controller diagnostics."""

from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.components.homekit_controller.const import KNOWN_DEVICES
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from .common import setup_accessories_from_file, setup_test_accessories

from tests.components.diagnostics import (
    get_diagnostics_for_config_entry,
    get_diagnostics_for_device,
)
from tests.typing import ClientSessionGenerator


async def test_config_entry(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test generating diagnostics for a config entry."""
    accessories = await setup_accessories_from_file(menuai, "koogeek_ls1.json")
    config_entry, _ = await setup_test_accessories(menuai, accessories)

    diag = await get_diagnostics_for_config_entry(menuai, menuai_client, config_entry)

    assert diag == snapshot(
        exclude=props("last_changed", "last_reported", "last_updated")
    )


async def test_device(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    device_registry: dr.DeviceRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test generating diagnostics for a device entry."""
    accessories = await setup_accessories_from_file(menuai, "koogeek_ls1.json")
    config_entry, _ = await setup_test_accessories(menuai, accessories)

    connection = menuai.data[KNOWN_DEVICES]["00:00:00:00:00:00"]
    device = device_registry.async_get(connection.devices[1])

    diag = await get_diagnostics_for_device(menuai, menuai_client, config_entry, device)

    assert diag == snapshot(
        exclude=props("last_changed", "last_reported", "last_updated")
    )
