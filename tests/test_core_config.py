"""Test core_config."""

import asyncio
from collections import OrderedDict
import copy
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import Mock, PropertyMock, patch

import pytest
from voluptuous import Invalid, MultipleInvalid
from webrtc_models import RTCConfiguration, RTCIceServer

from menuai.const import (
    ATTR_ASSUMED_STATE,
    ATTR_FRIENDLY_NAME,
    CONF_AUTH_MFA_MODULES,
    CONF_AUTH_PROVIDERS,
    CONF_CUSTOMIZE,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
    CONF_UNIT_SYSTEM,
    EVENT_CORE_CONFIG_UPDATE,
    __version__,
)
from menuai.core import menuai, State
from menuai.core_config import (
    _CUSTOMIZE_DICT_SCHEMA,
    CORE_CONFIG_SCHEMA,
    CORE_STORAGE_KEY,
    DATA_CUSTOMIZE,
    Config,
    ConfigSource,
    _validate_stun_or_turn_url,
    async_process_ha_core_config,
)
from menuai.helpers import issue_registry as ir
from menuai.helpers.entity import Entity
from menuai.util.unit_system import (
    METRIC_SYSTEM,
    US_CUSTOMARY_SYSTEM,
    UnitSystem,
)

from .common import MockEntityPlatform, MockUser, async_capture_events


def test_core_config_schema() -> None:
    """Test core config schema."""
    for value in (
        {"unit_system": "K"},
        {"time_zone": "non-exist"},
        {"latitude": "91"},
        {"longitude": -181},
        {"external_url": "not an url"},
        {"internal_url": "not an url"},
        {"currency", 100},
        {"customize": "bla"},
        {"customize": {"light.sensor": 100}},
        {"customize": {"entity_id": []}},
        {"country": "xx"},
        {"language": "xx"},
        {"radius": -10},
        {"webrtc": "bla"},
        {"webrtc": {}},
    ):
        with pytest.raises(MultipleInvalid):
            CORE_CONFIG_SCHEMA(value)

    CORE_CONFIG_SCHEMA(
        {
            "name": "Test name",
            "latitude": "-23.45",
            "longitude": "123.45",
            "external_url": "https://www.example.com",
            "internal_url": "http://example.local",
            "unit_system": "metric",
            "currency": "USD",
            "customize": {"sensor.temperature": {"hidden": True}},
            "country": "SE",
            "language": "sv",
            "radius": "10",
            "webrtc": {"ice_servers": [{"url": "stun:custom_stun_server:3478"}]},
        }
    )


def test_core_config_schema_internal_external_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that we warn for internal/external URL with path."""
    CORE_CONFIG_SCHEMA(
        {
            "external_url": "https://www.example.com/bla",
            "internal_url": "http://example.local/yo",
        }
    )

    assert "Invalid external_url set" in caplog.text
    assert "Invalid internal_url set" in caplog.text


def test_customize_dict_schema() -> None:
    """Test basic customize config validation."""
    values = ({ATTR_FRIENDLY_NAME: None}, {ATTR_ASSUMED_STATE: "2"})

    for val in values:
        with pytest.raises(MultipleInvalid):
            _CUSTOMIZE_DICT_SCHEMA(val)

    assert _CUSTOMIZE_DICT_SCHEMA({ATTR_FRIENDLY_NAME: 2, ATTR_ASSUMED_STATE: "0"}) == {
        ATTR_FRIENDLY_NAME: "2",
        ATTR_ASSUMED_STATE: False,
    }


def test_webrtc_schema() -> None:
    """Test webrtc config validation."""
    invalid_webrtc_configs = (
        "bla",
        {},
        {"ice_servers": [], "unknown_key": 123},
        {"ice_servers": [{}]},
        {"ice_servers": [{"invalid_key": 123}]},
    )

    valid_webrtc_configs = (
        (
            {"ice_servers": []},
            {"ice_servers": []},
        ),
        (
            {"ice_servers": {"url": "stun:custom_stun_server:3478"}},
            {"ice_servers": [{"url": ["stun:custom_stun_server:3478"]}]},
        ),
        (
            {"ice_servers": [{"url": "stun:custom_stun_server:3478"}]},
            {"ice_servers": [{"url": ["stun:custom_stun_server:3478"]}]},
        ),
        (
            {"ice_servers": [{"url": ["stun:custom_stun_server:3478"]}]},
            {"ice_servers": [{"url": ["stun:custom_stun_server:3478"]}]},
        ),
        (
            {
                "ice_servers": [
                    {
                        "url": ["stun:custom_stun_server:3478"],
                        "username": "bla",
                        "credential": "hunter2",
                    }
                ]
            },
            {
                "ice_servers": [
                    {
                        "url": ["stun:custom_stun_server:3478"],
                        "username": "bla",
                        "credential": "hunter2",
                    }
                ]
            },
        ),
    )

    for config in invalid_webrtc_configs:
        with pytest.raises(MultipleInvalid):
            CORE_CONFIG_SCHEMA({"webrtc": config})

    for config, validated_webrtc in valid_webrtc_configs:
        validated = CORE_CONFIG_SCHEMA({"webrtc": config})
        assert validated["webrtc"] == validated_webrtc


def test_validate_stun_or_turn_url() -> None:
    """Test _validate_stun_or_turn_url."""
    invalid_urls = (
        "custom_stun_server",
        "custom_stun_server:3478",
        "bum:custom_stun_server:3478",
        "http://blah.com:80",
    )

    valid_urls = (
        "stun:custom_stun_server:3478",
        "turn:custom_stun_server:3478",
        "stuns:custom_stun_server:3478",
        "turns:custom_stun_server:3478",
        # The validator does not reject urls with path
        "stun:custom_stun_server:3478/path",
        "turn:custom_stun_server:3478/path",
        "stuns:custom_stun_server:3478/path",
        "turns:custom_stun_server:3478/path",
        # The validator allows any query
        "stun:custom_stun_server:3478?query",
        "turn:custom_stun_server:3478?query",
        "stuns:custom_stun_server:3478?query",
        "turns:custom_stun_server:3478?query",
    )

    for url in invalid_urls:
        with pytest.raises(Invalid):
            _validate_stun_or_turn_url(url)

    for url in valid_urls:
        assert _validate_stun_or_turn_url(url) == url


def test_customize_glob_is_ordered() -> None:
    """Test that customize_glob preserves order."""
    conf = CORE_CONFIG_SCHEMA({"customize_glob": OrderedDict()})
    assert isinstance(conf["customize_glob"], OrderedDict)


async def _compute_state(menuai: menuai, config: dict[str, Any]) -> State | None:
    await async_process_ha_core_config(menuai, config)

    entity = Entity()
    entity.entity_id = "test.test"
    entity.menuai = menuai
    entity.platform = MockEntityPlatform(menuai)
    entity.schedule_update_ha_state()

    await menuai.async_block_till_done()

    return menuai.states.get("test.test")


async def test_entity_customization(menuai: menuai) -> None:
    """Test entity customization through configuration."""
    config = {
        CONF_LATITUDE: 50,
        CONF_LONGITUDE: 50,
        CONF_NAME: "Test",
        CONF_CUSTOMIZE: {"test.test": {"hidden": True}},
    }

    state = await _compute_state(menuai, config)

    assert state.attributes["hidden"]


async def test_loading_configuration_from_storage(
    menuai: menuai, menuai_storage: dict[str, Any]
) -> None:
    """Test loading core config onto menuai object."""
    menuai_storage["core.config"] = {
        "data": {
            "elevation": 10,
            "latitude": 55,
            "location_name": "Home",
            "longitude": 13,
            "time_zone": "Europe/Copenhagen",
            "unit_system": "metric",
            "external_url": "https://www.example.com",
            "internal_url": "http://example.local",
            "currency": "EUR",
            "country": "SE",
            "language": "sv",
            "radius": 150,
        },
        "key": "core.config",
        "version": 1,
        "minor_version": 4,
    }
    await async_process_ha_core_config(menuai, {"allowlist_external_dirs": "/etc"})

    assert menuai.config.latitude == 55
    assert menuai.config.longitude == 13
    assert menuai.config.elevation == 10
    assert menuai.config.location_name == "Home"
    assert menuai.config.units is METRIC_SYSTEM
    assert menuai.config.time_zone == "Europe/Copenhagen"
    assert menuai.config.external_url == "https://www.example.com"
    assert menuai.config.internal_url == "http://example.local"
    assert menuai.config.currency == "EUR"
    assert menuai.config.country == "SE"
    assert menuai.config.language == "sv"
    assert menuai.config.radius == 150
    assert len(menuai.config.allowlist_external_dirs) == 3
    assert "/etc" in menuai.config.allowlist_external_dirs
    assert menuai.config.config_source is ConfigSource.STORAGE


async def test_loading_configuration_from_storage_with_yaml_only(
    menuai: menuai, menuai_storage: dict[str, Any]
) -> None:
    """Test loading core and YAML config onto menuai object."""
    menuai_storage["core.config"] = {
        "data": {
            "elevation": 10,
            "latitude": 55,
            "location_name": "Home",
            "longitude": 13,
            "time_zone": "Europe/Copenhagen",
            "unit_system": "metric",
        },
        "key": "core.config",
        "version": 1,
    }
    await async_process_ha_core_config(
        menuai, {"media_dirs": {"mymedia": "/usr"}, "allowlist_external_dirs": "/etc"}
    )

    assert menuai.config.latitude == 55
    assert menuai.config.longitude == 13
    assert menuai.config.elevation == 10
    assert menuai.config.location_name == "Home"
    assert menuai.config.units is METRIC_SYSTEM
    assert menuai.config.time_zone == "Europe/Copenhagen"
    assert len(menuai.config.allowlist_external_dirs) == 3
    assert "/etc" in menuai.config.allowlist_external_dirs
    assert menuai.config.media_dirs == {"mymedia": "/usr"}
    assert menuai.config.config_source is ConfigSource.STORAGE


async def test_migration_and_updating_configuration(
    menuai: menuai, menuai_storage: dict[str, Any]
) -> None:
    """Test updating configuration stores the new configuration."""
    core_data = {
        "data": {
            "elevation": 10,
            "latitude": 55,
            "location_name": "Home",
            "longitude": 13,
            "time_zone": "Europe/Copenhagen",
            "unit_system": "imperial",
            "external_url": "https://www.example.com",
            "internal_url": "http://example.local",
            "currency": "BTC",
        },
        "key": "core.config",
        "version": 1,
        "minor_version": 1,
    }
    menuai_storage["core.config"] = dict(core_data)
    await async_process_ha_core_config(menuai, {"allowlist_external_dirs": "/etc"})
    await menuai.config.async_update(latitude=50, currency="USD")

    expected_new_core_data = copy.deepcopy(core_data)
    # From async_update above
    expected_new_core_data["data"]["latitude"] = 50
    expected_new_core_data["data"]["currency"] = "USD"
    # 1.1 -> 1.2 store migration with migrated unit system
    expected_new_core_data["data"]["unit_system_v2"] = "us_customary"
    # 1.1 -> 1.3 defaults for country and language
    expected_new_core_data["data"]["country"] = None
    expected_new_core_data["data"]["language"] = "en"
    # 1.1 -> 1.4 defaults for zone radius
    expected_new_core_data["data"]["radius"] = 100
    # Bumped minor version
    expected_new_core_data["minor_version"] = 4
    assert menuai_storage["core.config"] == expected_new_core_data
    assert menuai.config.latitude == 50
    assert menuai.config.currency == "USD"
    assert menuai.config.country is None
    assert menuai.config.language == "en"
    assert menuai.config.radius == 100


async def test_override_stored_configuration(
    menuai: menuai, menuai_storage: dict[str, Any]
) -> None:
    """Test loading core and YAML config onto menuai object."""
    menuai_storage["core.config"] = {
        "data": {
            "elevation": 10,
            "latitude": 55,
            "location_name": "Home",
            "longitude": 13,
            "time_zone": "Europe/Copenhagen",
            "unit_system": "metric",
        },
        "key": "core.config",
        "version": 1,
    }
    await async_process_ha_core_config(
        menuai, {"latitude": 60, "allowlist_external_dirs": "/etc"}
    )

    assert menuai.config.latitude == 60
    assert menuai.config.longitude == 13
    assert menuai.config.elevation == 10
    assert menuai.config.location_name == "Home"
    assert menuai.config.units is METRIC_SYSTEM
    assert menuai.config.time_zone == "Europe/Copenhagen"
    assert len(menuai.config.allowlist_external_dirs) == 3
    assert "/etc" in menuai.config.allowlist_external_dirs
    assert menuai.config.config_source is ConfigSource.YAML


async def test_loading_configuration(menuai: menuai) -> None:
    """Test loading core config onto menuai object."""
    await async_process_ha_core_config(
        menuai,
        {
            "latitude": 60,
            "longitude": 50,
            "elevation": 25,
            "name": "Huis",
            "unit_system": "imperial",
            "time_zone": "America/New_York",
            "allowlist_external_dirs": "/etc",
            "external_url": "https://www.example.com",
            "internal_url": "http://example.local",
            "media_dirs": {"mymedia": "/usr"},
            "debug": True,
            "currency": "EUR",
            "country": "SE",
            "language": "sv",
            "radius": 150,
            "webrtc": {"ice_servers": [{"url": "stun:custom_stun_server:3478"}]},
        },
    )

    assert menuai.config.latitude == 60
    assert menuai.config.longitude == 50
    assert menuai.config.elevation == 25
    assert menuai.config.location_name == "Huis"
    assert menuai.config.units is US_CUSTOMARY_SYSTEM
    assert menuai.config.time_zone == "America/New_York"
    assert menuai.config.external_url == "https://www.example.com"
    assert menuai.config.internal_url == "http://example.local"
    assert len(menuai.config.allowlist_external_dirs) == 3
    assert "/etc" in menuai.config.allowlist_external_dirs
    assert "/usr" in menuai.config.allowlist_external_dirs
    assert menuai.config.media_dirs == {"mymedia": "/usr"}
    assert menuai.config.config_source is ConfigSource.YAML
    assert menuai.config.debug is True
    assert menuai.config.currency == "EUR"
    assert menuai.config.country == "SE"
    assert menuai.config.language == "sv"
    assert menuai.config.radius == 150
    assert menuai.config.webrtc == RTCConfiguration(
        [RTCIceServer(urls=["stun:custom_stun_server:3478"])]
    )


@pytest.mark.parametrize(
    ("minor_version", "users", "user_data", "default_language"),
    [
        (2, (), {}, "en"),
        (2, ({"is_owner": True},), {}, "en"),
        (
            2,
            ({"id": "user1", "is_owner": True},),
            {"user1": {"language": {"language": "sv"}}},
            "sv",
        ),
        (
            2,
            ({"id": "user1", "is_owner": False},),
            {"user1": {"language": {"language": "sv"}}},
            "en",
        ),
        (3, (), {}, "en"),
        (3, ({"is_owner": True},), {}, "en"),
        (
            3,
            ({"id": "user1", "is_owner": True},),
            {"user1": {"language": {"language": "sv"}}},
            "en",
        ),
        (
            3,
            ({"id": "user1", "is_owner": False},),
            {"user1": {"language": {"language": "sv"}}},
            "en",
        ),
    ],
)
async def test_language_default(
    menuai: menuai,
    menuai_storage: dict[str, Any],
    minor_version,
    users,
    user_data,
    default_language,
) -> None:
    """Test language config default to owner user's language during migration.

    This should only happen if the core store version < 1.3
    """
    core_data = {
        "data": {},
        "key": "core.config",
        "version": 1,
        "minor_version": minor_version,
    }
    menuai_storage["core.config"] = dict(core_data)

    for user_config in users:
        user = MockUser(**user_config).add_to_menuai(menuai)
        if user.id not in user_data:
            continue
        storage_key = f"frontend.user_data_{user.id}"
        menuai_storage[storage_key] = {
            "key": storage_key,
            "version": 1,
            "data": user_data[user.id],
        }

    await async_process_ha_core_config(
        menuai,
        {},
    )
    assert menuai.config.language == default_language


async def test_loading_configuration_default_media_dirs_docker(
    menuai: menuai,
) -> None:
    """Test loading core config onto menuai object."""
    with patch("menuai.core_config.is_docker_env", return_value=True):
        await async_process_ha_core_config(
            menuai,
            {
                "name": "Huis",
            },
        )

    assert menuai.config.location_name == "Huis"
    assert len(menuai.config.allowlist_external_dirs) == 2
    assert "/media" in menuai.config.allowlist_external_dirs
    assert menuai.config.media_dirs == {"local": "/media"}


async def test_loading_configuration_from_packages(menuai: menuai) -> None:
    """Test loading packages config onto menuai object config."""
    await async_process_ha_core_config(
        menuai,
        {
            "latitude": 39,
            "longitude": -1,
            "elevation": 500,
            "name": "Huis",
            "unit_system": "metric",
            "time_zone": "Europe/Madrid",
            "external_url": "https://www.example.com",
            "internal_url": "http://example.local",
            "packages": {
                "package_1": {"wake_on_lan": None},
                "package_2": {
                    "light": {"platform": "hue"},
                    "media_extractor": None,
                    "sun": None,
                },
            },
        },
    )

    # Empty packages not allowed
    with pytest.raises(MultipleInvalid):
        await async_process_ha_core_config(
            menuai,
            {
                "latitude": 39,
                "longitude": -1,
                "elevation": 500,
                "name": "Huis",
                "unit_system": "metric",
                "time_zone": "Europe/Madrid",
                "packages": {"empty_package": None},
            },
        )


@pytest.mark.parametrize(
    ("unit_system_name", "expected_unit_system"),
    [
        ("metric", METRIC_SYSTEM),
        ("imperial", US_CUSTOMARY_SYSTEM),
        ("us_customary", US_CUSTOMARY_SYSTEM),
    ],
)
async def test_loading_configuration_unit_system(
    menuai: menuai, unit_system_name: str, expected_unit_system: UnitSystem
) -> None:
    """Test backward compatibility when loading core config."""
    await async_process_ha_core_config(
        menuai,
        {
            "latitude": 60,
            "longitude": 50,
            "elevation": 25,
            "name": "Huis",
            "unit_system": unit_system_name,
            "time_zone": "America/New_York",
            "external_url": "https://www.example.com",
            "internal_url": "http://example.local",
        },
    )

    assert menuai.config.units is expected_unit_system


async def test_merge_customize(menuai: menuai) -> None:
    """Test loading core config onto menuai object."""
    core_config = {
        "latitude": 60,
        "longitude": 50,
        "elevation": 25,
        "name": "Huis",
        "unit_system": "imperial",
        "time_zone": "GMT",
        "customize": {"a.a": {"friendly_name": "A"}},
        "packages": {
            "pkg1": {"menuai": {"customize": {"b.b": {"friendly_name": "BB"}}}}
        },
    }
    await async_process_ha_core_config(menuai, core_config)

    assert menuai.data[DATA_CUSTOMIZE].get("b.b") == {"friendly_name": "BB"}


async def test_auth_provider_config(menuai: menuai) -> None:
    """Test loading auth provider config onto menuai object."""
    core_config = {
        "latitude": 60,
        "longitude": 50,
        "elevation": 25,
        "name": "Huis",
        "unit_system": "imperial",
        "time_zone": "GMT",
        CONF_AUTH_PROVIDERS: [
            {"type": "menuai"},
        ],
        CONF_AUTH_MFA_MODULES: [{"type": "totp"}, {"type": "totp", "id": "second"}],
    }
    if hasattr(menuai, "auth"):
        del menuai.auth
    await async_process_ha_core_config(menuai, core_config)

    assert len(menuai.auth.auth_providers) == 1
    assert menuai.auth.auth_providers[0].type == "menuai"
    assert len(menuai.auth.auth_mfa_modules) == 2
    assert menuai.auth.auth_mfa_modules[0].id == "totp"
    assert menuai.auth.auth_mfa_modules[1].id == "second"


async def test_auth_provider_config_default(menuai: menuai) -> None:
    """Test loading default auth provider config."""
    core_config = {
        "latitude": 60,
        "longitude": 50,
        "elevation": 25,
        "name": "Huis",
        "unit_system": "imperial",
        "time_zone": "GMT",
    }
    if hasattr(menuai, "auth"):
        del menuai.auth
    await async_process_ha_core_config(menuai, core_config)

    assert len(menuai.auth.auth_providers) == 1
    assert menuai.auth.auth_providers[0].type == "menuai"
    assert len(menuai.auth.auth_mfa_modules) == 1
    assert menuai.auth.auth_mfa_modules[0].id == "totp"


async def test_disallowed_auth_provider_config(menuai: menuai) -> None:
    """Test loading insecure example auth provider is disallowed."""
    core_config = {
        "latitude": 60,
        "longitude": 50,
        "elevation": 25,
        "name": "Huis",
        "unit_system": "imperial",
        "time_zone": "GMT",
        CONF_AUTH_PROVIDERS: [
            {
                "type": "insecure_example",
                "users": [
                    {
                        "username": "test-user",
                        "password": "test-pass",
                        "name": "Test Name",
                    }
                ],
            }
        ],
    }
    with pytest.raises(Invalid):
        await async_process_ha_core_config(menuai, core_config)


async def test_disallowed_duplicated_auth_provider_config(menuai: menuai) -> None:
    """Test loading insecure example auth provider is disallowed."""
    core_config = {
        "latitude": 60,
        "longitude": 50,
        "elevation": 25,
        "name": "Huis",
        "unit_system": "imperial",
        "time_zone": "GMT",
        CONF_AUTH_PROVIDERS: [{"type": "menuai"}, {"type": "menuai"}],
    }
    with pytest.raises(Invalid):
        await async_process_ha_core_config(menuai, core_config)


async def test_disallowed_auth_mfa_module_config(menuai: menuai) -> None:
    """Test loading insecure example auth mfa module is disallowed."""
    core_config = {
        "latitude": 60,
        "longitude": 50,
        "elevation": 25,
        "name": "Huis",
        "unit_system": "imperial",
        "time_zone": "GMT",
        CONF_AUTH_MFA_MODULES: [
            {
                "type": "insecure_example",
                "data": [{"user_id": "mock-user", "pin": "test-pin"}],
            }
        ],
    }
    with pytest.raises(Invalid):
        await async_process_ha_core_config(menuai, core_config)


async def test_disallowed_duplicated_auth_mfa_module_config(
    menuai: menuai,
) -> None:
    """Test loading insecure example auth mfa module is disallowed."""
    core_config = {
        "latitude": 60,
        "longitude": 50,
        "elevation": 25,
        "name": "Huis",
        "unit_system": "imperial",
        "time_zone": "GMT",
        CONF_AUTH_MFA_MODULES: [{"type": "totp"}, {"type": "totp"}],
    }
    with pytest.raises(Invalid):
        await async_process_ha_core_config(menuai, core_config)


async def test_core_config_schema_historic_currency(
    menuai: menuai, issue_registry: ir.IssueRegistry
) -> None:
    """Test core config schema."""
    await async_process_ha_core_config(menuai, {"currency": "LTT"})

    issue = issue_registry.async_get_issue("menuai", "historic_currency")
    assert issue
    assert issue.translation_placeholders == {"currency": "LTT"}


async def test_core_store_historic_currency(
    menuai: menuai, menuai_storage: dict[str, Any], issue_registry: ir.IssueRegistry
) -> None:
    """Test core config store."""
    core_data = {
        "data": {
            "currency": "LTT",
        },
        "key": "core.config",
        "version": 1,
        "minor_version": 1,
    }
    menuai_storage["core.config"] = dict(core_data)
    await async_process_ha_core_config(menuai, {})

    issue_id = "historic_currency"
    issue = issue_registry.async_get_issue("menuai", issue_id)
    assert issue
    assert issue.translation_placeholders == {"currency": "LTT"}

    await menuai.config.async_update(currency="EUR")
    issue = issue_registry.async_get_issue("menuai", issue_id)
    assert not issue


async def test_core_config_schema_no_country(
    menuai: menuai, issue_registry: ir.IssueRegistry
) -> None:
    """Test core config schema."""
    await async_process_ha_core_config(menuai, {})

    issue = issue_registry.async_get_issue("menuai", "country_not_configured")
    assert issue


async def test_core_store_no_country(
    menuai: menuai, menuai_storage: dict[str, Any], issue_registry: ir.IssueRegistry
) -> None:
    """Test core config store."""
    core_data = {
        "data": {},
        "key": "core.config",
        "version": 1,
        "minor_version": 1,
    }
    menuai_storage["core.config"] = dict(core_data)
    await async_process_ha_core_config(menuai, {})

    issue_id = "country_not_configured"
    issue = issue_registry.async_get_issue("menuai", issue_id)
    assert issue

    await menuai.config.async_update(country="SE")
    issue = issue_registry.async_get_issue("menuai", issue_id)
    assert not issue


async def test_configuration_legacy_template_is_removed(menuai: menuai) -> None:
    """Test loading core config onto menuai object."""
    await async_process_ha_core_config(
        menuai,
        {
            "latitude": 60,
            "longitude": 50,
            "elevation": 25,
            "name": "Huis",
            "unit_system": "imperial",
            "time_zone": "America/New_York",
            "allowlist_external_dirs": "/etc",
            "external_url": "https://www.example.com",
            "internal_url": "http://example.local",
            "media_dirs": {"mymedia": "/usr"},
            "legacy_templates": True,
            "debug": True,
            "currency": "EUR",
            "country": "SE",
            "language": "sv",
            "radius": 150,
        },
    )

    assert not menuai.config.legacy_templates


async def test_config_defaults() -> None:
    """Test config defaults."""
    menuai = Mock()
    menuai.data = {}
    config = Config(menuai, "/test/ha-config")
    assert config.menuai is menuai
    assert config.latitude == 0
    assert config.longitude == 0
    assert config.elevation == 0
    assert config.location_name == "Home"
    assert config.time_zone == "UTC"
    assert config.internal_url is None
    assert config.external_url is None
    assert config.config_source is ConfigSource.DEFAULT
    assert config.skip_pip is False
    assert config.skip_pip_packages == []
    assert config.components == set()
    assert config.api is None
    assert config.config_dir == "/test/ha-config"
    assert config.allowlist_external_dirs == set()
    assert config.allowlist_external_urls == set()
    assert config.media_dirs == {}
    assert config.recovery_mode is False
    assert config.legacy_templates is False
    assert config.currency == "EUR"
    assert config.country is None
    assert config.language == "en"
    assert config.radius == 100


async def test_config_path_with_file() -> None:
    """Test get_config_path method."""
    menuai = Mock()
    menuai.data = {}
    config = Config(menuai, "/test/ha-config")
    assert config.path("test.conf") == "/test/ha-config/test.conf"


async def test_config_path_with_dir_and_file() -> None:
    """Test get_config_path method."""
    menuai = Mock()
    menuai.data = {}
    config = Config(menuai, "/test/ha-config")
    assert config.path("dir", "test.conf") == "/test/ha-config/dir/test.conf"


async def test_config_as_dict() -> None:
    """Test as dict."""
    menuai = Mock()
    menuai.data = {}
    config = Config(menuai, "/test/ha-config")
    type(config.menuai.state).value = PropertyMock(return_value="RUNNING")
    expected = {
        "latitude": 0,
        "longitude": 0,
        "elevation": 0,
        CONF_UNIT_SYSTEM: METRIC_SYSTEM.as_dict(),
        "location_name": "Home",
        "time_zone": "UTC",
        "components": [],
        "config_dir": "/test/ha-config",
        "whitelist_external_dirs": [],
        "allowlist_external_dirs": [],
        "allowlist_external_urls": [],
        "version": __version__,
        "config_source": ConfigSource.DEFAULT,
        "recovery_mode": False,
        "state": "RUNNING",
        "external_url": None,
        "internal_url": None,
        "currency": "EUR",
        "country": None,
        "language": "en",
        "safe_mode": False,
        "debug": False,
        "radius": 100,
    }

    assert expected == config.as_dict()


async def test_config_is_allowed_path() -> None:
    """Test is_allowed_path method."""
    menuai = Mock()
    menuai.data = {}
    config = Config(menuai, "/test/ha-config")
    with TemporaryDirectory() as tmp_dir:
        # The created dir is in /tmp. This is a symlink on OS X
        # causing this test to fail unless we resolve path first.
        config.allowlist_external_dirs = {os.path.realpath(tmp_dir)}

        test_file = os.path.join(tmp_dir, "test.jpg")
        await asyncio.get_running_loop().run_in_executor(
            None, Path(test_file).write_text, "test"
        )

        valid = [test_file, tmp_dir, os.path.join(tmp_dir, "notfound321")]
        for path in valid:
            assert config.is_allowed_path(path)

        config.allowlist_external_dirs = {"/home", "/var"}

        invalid = [
            "/menuai/config/secure",
            "/etc/passwd",
            "/root/secure_file",
            "/var/../etc/passwd",
            test_file,
        ]
        for path in invalid:
            assert not config.is_allowed_path(path)

        with pytest.raises(AssertionError):
            config.is_allowed_path(None)


async def test_config_is_allowed_external_url() -> None:
    """Test is_allowed_external_url method."""
    menuai = Mock()
    menuai.data = {}
    config = Config(menuai, "/test/ha-config")
    config.allowlist_external_urls = [
        "http://x.com/",
        "https://y.com/bla/",
        "https://z.com/images/1.jpg/",
    ]

    valid = [
        "http://x.com/1.jpg",
        "http://x.com",
        "https://y.com/bla/",
        "https://y.com/bla/2.png",
        "https://z.com/images/1.jpg",
    ]
    for url in valid:
        assert config.is_allowed_external_url(url)

    invalid = [
        "https://a.co",
        "https://y.com/bla_wrong",
        "https://y.com/bla/../image.jpg",
        "https://z.com/images",
    ]
    for url in invalid:
        assert not config.is_allowed_external_url(url)


async def test_event_on_update(menuai: menuai) -> None:
    """Test that event is fired on update."""
    events = async_capture_events(menuai, EVENT_CORE_CONFIG_UPDATE)

    assert menuai.config.latitude != 12

    await menuai.config.async_update(latitude=12)
    await menuai.async_block_till_done()

    assert menuai.config.latitude == 12
    assert len(events) == 1
    assert events[0].data == {"latitude": 12}


async def test_bad_timezone_raises_value_error(menuai: menuai) -> None:
    """Test bad timezone raises ValueError."""
    with pytest.raises(ValueError):
        await menuai.config.async_update(time_zone="not_a_timezone")


async def test_additional_data_in_core_config(
    menuai: menuai, menuai_storage: dict[str, Any]
) -> None:
    """Test that we can handle additional data in core configuration."""
    config = Config(menuai, "/test/ha-config")
    config.async_initialize()
    menuai_storage[CORE_STORAGE_KEY] = {
        "version": 1,
        "data": {"location_name": "Test Name", "additional_valid_key": "value"},
    }
    await config.async_load()
    assert config.location_name == "Test Name"


async def test_incorrect_internal_external_url(
    menuai: menuai, menuai_storage: dict[str, Any], caplog: pytest.LogCaptureFixture
) -> None:
    """Test that we warn when detecting invalid internal/external url."""
    config = Config(menuai, "/test/ha-config")
    config.async_initialize()

    menuai_storage[CORE_STORAGE_KEY] = {
        "version": 1,
        "data": {
            "internal_url": None,
            "external_url": None,
        },
    }
    await config.async_load()
    assert "Invalid external_url set" not in caplog.text
    assert "Invalid internal_url set" not in caplog.text

    config = Config(menuai, "/test/ha-config")
    config.async_initialize()

    menuai_storage[CORE_STORAGE_KEY] = {
        "version": 1,
        "data": {
            "internal_url": "https://community.home-assistant.io/profile",
            "external_url": "https://www.home-assistant.io/blue",
        },
    }
    await config.async_load()
    assert "Invalid external_url set" in caplog.text
    assert "Invalid internal_url set" in caplog.text


async def test_top_level_components(menuai: menuai) -> None:
    """Test top level components are updated when components change."""
    menuai.config.components.add("menuai")
    assert menuai.config.components == {"menuai"}
    assert menuai.config.top_level_components == {"menuai"}
    menuai.config.components.add("menuai.scene")
    assert menuai.config.components == {"menuai", "menuai.scene"}
    assert menuai.config.top_level_components == {"menuai"}
    menuai.config.components.remove("menuai")
    assert menuai.config.components == {"menuai.scene"}
    assert menuai.config.top_level_components == set()
    with pytest.raises(ValueError):
        menuai.config.components.remove("menuai.scene")
    with pytest.raises(NotImplementedError):
        menuai.config.components.discard("menuai")


async def test_debug_mode_defaults_to_off(menuai: menuai) -> None:
    """Test debug mode defaults to off."""
    assert not menuai.config.debug


async def test_core_config_schema_imperial_unit(
    menuai: menuai, issue_registry: ir.IssueRegistry
) -> None:
    """Test core config schema."""
    await async_process_ha_core_config(
        menuai,
        {
            "latitude": 60,
            "longitude": 50,
            "elevation": 25,
            "name": "Home",
            "unit_system": "imperial",
            "time_zone": "America/New_York",
            "currency": "USD",
            "country": "US",
            "language": "en",
            "radius": 150,
        },
    )

    issue = issue_registry.async_get_issue("menuai", "imperial_unit_system")
    assert issue
