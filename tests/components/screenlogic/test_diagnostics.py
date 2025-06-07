"""Testing for ScreenLogic diagnostics."""

from unittest.mock import DEFAULT, patch

from screenlogicpy import ScreenLogicGateway
from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.core import menuai
from menuai.helpers import device_registry as dr

from . import (
    DATA_FULL_CHEM,
    GATEWAY_DISCOVERY_IMPORT_PATH,
    MOCK_ADAPTER_MAC,
    stub_async_connect,
)

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    device_registry: dr.DeviceRegistry,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test diagnostics."""
    mock_config_entry.add_to_menuai(menuai)

    device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, MOCK_ADAPTER_MAC)},
    )
    with (
        patch(
            GATEWAY_DISCOVERY_IMPORT_PATH,
            return_value={},
        ),
        patch.multiple(
            ScreenLogicGateway,
            async_connect=lambda *args, **kwargs: stub_async_connect(
                DATA_FULL_CHEM, *args, **kwargs
            ),
            is_connected=True,
            _async_connected_request=DEFAULT,
            get_debug=lambda self: {},
        ),
    ):
        assert await menuai.config_entries.async_setup(mock_config_entry.entry_id)
        await menuai.async_block_till_done()

        diag = await get_diagnostics_for_config_entry(
            menuai, menuai_client, mock_config_entry
        )

    assert diag == snapshot(exclude=props("created_at", "modified_at"))
