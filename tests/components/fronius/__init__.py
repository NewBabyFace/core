"""Tests for the Fronius integration."""

from __future__ import annotations

from collections.abc import Callable
import json
from typing import Any

from menuai.components.fronius.const import DOMAIN
from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST
from menuai.core import menuai
from menuai.helpers.typing import UNDEFINED, UndefinedType

from tests.common import MockConfigEntry, load_fixture
from tests.test_util.aiohttp import AiohttpClientMocker

MOCK_HOST = "http://fronius"
MOCK_UID = "123.4567890"


async def setup_fronius_integration(
    menuai: menuai, is_logger: bool = True, unique_id: str = MOCK_UID
) -> ConfigEntry:
    """Create the Fronius integration."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="f1e2b9837e8adaed6fa682acaa216fd8",
        unique_id=unique_id,  # has to match mocked logger unique_id
        data={
            CONF_HOST: MOCK_HOST,
            "is_logger": is_logger,
        },
    )
    entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    return entry


def _load_and_patch_fixture(
    override_data: dict[str, list[tuple[list[str], Any]]],
) -> Callable[[str, str | None], str]:
    """Return a fixture loader that patches values at nested keys for a given filename."""

    def load_and_patch(filename: str, integration: str):
        """Load a fixture and patch given values."""
        text = load_fixture(filename, integration)
        if filename not in override_data:
            return text

        _loaded = json.loads(text)
        for keys, value in override_data[filename]:
            _dic = _loaded
            for key in keys[:-1]:
                _dic = _dic[key]
            _dic[keys[-1]] = value
        return json.dumps(_loaded)

    return load_and_patch


def mock_responses(
    aioclient_mock: AiohttpClientMocker,
    host: str = MOCK_HOST,
    fixture_set: str = "symo",
    inverter_ids: list[str | int] | UndefinedType = UNDEFINED,
    night: bool = False,
    override_data: dict[str, list[tuple[list[str], Any]]]
    | None = None,  # {filename: [([list of nested keys], patch_value)]}
) -> None:
    """Mock responses for Fronius devices."""
    aioclient_mock.clear_requests()
    _night = "_night" if night else ""
    _load = _load_and_patch_fixture(override_data) if override_data else load_fixture

    aioclient_mock.get(
        f"{host}/solar_api/GetAPIVersion.cgi",
        text=_load(f"{fixture_set}/GetAPIVersion.json", "fronius"),
    )
    for inverter_id in [1] if inverter_ids is UNDEFINED else inverter_ids:
        aioclient_mock.get(
            f"{host}/solar_api/v1/GetInverterRealtimeData.cgi?Scope=Device&"
            f"DeviceId={inverter_id}&DataCollection=CommonInverterData",
            text=_load(
                f"{fixture_set}/GetInverterRealtimeData_Device_{inverter_id}{_night}.json",
                "fronius",
            ),
        )
    aioclient_mock.get(
        f"{host}/solar_api/v1/GetInverterInfo.cgi",
        text=_load(f"{fixture_set}/GetInverterInfo{_night}.json", "fronius"),
    )
    aioclient_mock.get(
        f"{host}/solar_api/v1/GetLoggerInfo.cgi",
        text=_load(f"{fixture_set}/GetLoggerInfo.json", "fronius"),
    )
    aioclient_mock.get(
        f"{host}/solar_api/v1/GetMeterRealtimeData.cgi?Scope=System",
        text=_load(f"{fixture_set}/GetMeterRealtimeData.json", "fronius"),
    )
    aioclient_mock.get(
        f"{host}/solar_api/v1/GetPowerFlowRealtimeData.fcgi",
        text=_load(f"{fixture_set}/GetPowerFlowRealtimeData{_night}.json", "fronius"),
    )
    aioclient_mock.get(
        f"{host}/solar_api/v1/GetStorageRealtimeData.cgi?Scope=System",
        text=_load(f"{fixture_set}/GetStorageRealtimeData.json", "fronius"),
    )
    aioclient_mock.get(
        f"{host}/solar_api/v1/GetOhmPilotRealtimeData.cgi?Scope=System",
        text=_load(f"{fixture_set}/GetOhmPilotRealtimeData.json", "fronius"),
    )
