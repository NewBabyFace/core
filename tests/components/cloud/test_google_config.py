"""Test the Cloud Google Config."""

from http import HTTPStatus
from unittest.mock import Mock, PropertyMock, patch

from freezegun import freeze_time
import pytest

from menuai.components.cloud import GACTIONS_SCHEMA
from menuai.components.cloud.const import (
    DATA_CLOUD,
    PREF_DISABLE_2FA,
    PREF_GOOGLE_DEFAULT_EXPOSE,
    PREF_GOOGLE_ENTITY_CONFIGS,
    PREF_SHOULD_EXPOSE,
)
from menuai.components.cloud.google_config import CloudGoogleConfig
from menuai.components.cloud.prefs import CloudPreferences
from menuai.components.google_assistant import helpers as ga_helpers
from menuai.components.menuai.exposed_entities import (
    DATA_EXPOSED_ENTITIES,
    async_expose_entity,
    async_get_entity_settings,
)
from menuai.const import (
    EVENT_menuai_START,
    EVENT_menuai_STARTED,
    EntityCategory,
)
from menuai.core import CoreState, menuai, State
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.setup import async_setup_component
from menuai.util.dt import utcnow

from tests.common import MockConfigEntry, async_fire_time_changed


@pytest.fixture
def mock_conf(menuai: menuai, cloud_prefs: CloudPreferences) -> CloudGoogleConfig:
    """Mock Google conf."""
    return CloudGoogleConfig(
        menuai,
        GACTIONS_SCHEMA({}),
        "mock-user-id",
        cloud_prefs,
        Mock(username="abcdefghjkl"),
    )


def expose_new(menuai: menuai, expose_new: bool) -> None:
    """Enable exposing new entities to Google."""
    exposed_entities = menuai.data[DATA_EXPOSED_ENTITIES]
    exposed_entities.async_set_expose_new_entities("cloud.google_assistant", expose_new)


def expose_entity(menuai: menuai, entity_id: str, should_expose: bool) -> None:
    """Expose an entity to Google."""
    async_expose_entity(menuai, "cloud.google_assistant", entity_id, should_expose)


async def test_google_update_report_state(
    mock_conf: CloudGoogleConfig, menuai: menuai, cloud_prefs: CloudPreferences
) -> None:
    """Test Google config responds to updating preference."""
    assert await async_setup_component(menuai, "menuai", {})

    await mock_conf.async_initialize()
    await mock_conf.async_connect_agent_user("mock-user-id")

    mock_conf._cloud.subscription_expired = False

    with (
        patch.object(mock_conf, "async_sync_entities") as mock_sync,
        patch(
            "menuai.components.google_assistant.report_state.async_enable_report_state"
        ) as mock_report_state,
    ):
        await cloud_prefs.async_update(google_report_state=True)
        await menuai.async_block_till_done()

    assert len(mock_sync.mock_calls) == 1
    assert len(mock_report_state.mock_calls) == 1


async def test_google_update_report_state_subscription_expired(
    mock_conf: CloudGoogleConfig, menuai: menuai, cloud_prefs: CloudPreferences
) -> None:
    """Test Google config not reporting state when subscription has expired."""
    assert await async_setup_component(menuai, "menuai", {})

    await mock_conf.async_initialize()
    await mock_conf.async_connect_agent_user("mock-user-id")

    assert mock_conf._cloud.subscription_expired

    with (
        patch.object(mock_conf, "async_sync_entities") as mock_sync,
        patch(
            "menuai.components.google_assistant.report_state.async_enable_report_state"
        ) as mock_report_state,
    ):
        await cloud_prefs.async_update(google_report_state=True)
        await menuai.async_block_till_done()

    assert len(mock_sync.mock_calls) == 0
    assert len(mock_report_state.mock_calls) == 0


async def test_sync_entities(
    mock_conf: CloudGoogleConfig, menuai: menuai, cloud_prefs: CloudPreferences
) -> None:
    """Test sync devices."""
    assert await async_setup_component(menuai, "menuai", {})

    await mock_conf.async_initialize()
    assert len(mock_conf.async_get_agent_users()) == 0

    await mock_conf.async_connect_agent_user("mock-user-id")

    assert len(mock_conf.async_get_agent_users()) == 1

    with patch(
        "menuai_nabucasa.cloud_api.async_google_actions_request_sync",
        return_value=Mock(status=HTTPStatus.NOT_FOUND),
    ) as mock_request_sync:
        assert (
            await mock_conf.async_sync_entities("mock-user-id") == HTTPStatus.NOT_FOUND
        )
        assert len(mock_conf.async_get_agent_users()) == 0
        assert len(mock_request_sync.mock_calls) == 1


async def test_google_update_expose_trigger_sync(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    cloud_prefs: CloudPreferences,
) -> None:
    """Test Google config responds to updating exposed entities."""
    assert await async_setup_component(menuai, "menuai", {})

    # Enable exposing new entities to Google
    expose_new(menuai, True)
    # Register entities
    binary_sensor_entry = entity_registry.async_get_or_create(
        "binary_sensor", "test", "unique", suggested_object_id="door"
    )
    sensor_entry = entity_registry.async_get_or_create(
        "sensor", "test", "unique", suggested_object_id="temp"
    )
    light_entry = entity_registry.async_get_or_create(
        "light", "test", "unique", suggested_object_id="kitchen"
    )

    with freeze_time(utcnow()):
        config = CloudGoogleConfig(
            menuai,
            GACTIONS_SCHEMA({}),
            "mock-user-id",
            cloud_prefs,
            Mock(username="abcdefghjkl"),
        )
        await config.async_initialize()
        menuai.bus.async_fire(EVENT_menuai_STARTED)
        await menuai.async_block_till_done()
        await config.async_connect_agent_user("mock-user-id")

        with (
            patch.object(config, "async_sync_entities") as mock_sync,
            patch.object(ga_helpers, "SYNC_DELAY", 0),
        ):
            expose_entity(menuai, light_entry.entity_id, True)
            await menuai.async_block_till_done()
            async_fire_time_changed(menuai, utcnow())
            await menuai.async_block_till_done()

        assert len(mock_sync.mock_calls) == 1

        with (
            patch.object(config, "async_sync_entities") as mock_sync,
            patch.object(ga_helpers, "SYNC_DELAY", 0),
        ):
            expose_entity(menuai, light_entry.entity_id, False)
            expose_entity(menuai, binary_sensor_entry.entity_id, True)
            expose_entity(menuai, sensor_entry.entity_id, True)
            await menuai.async_block_till_done()
            async_fire_time_changed(menuai, utcnow())
            await menuai.async_block_till_done()

        assert len(mock_sync.mock_calls) == 1


@pytest.mark.usefixtures("mock_cloud_login")
async def test_google_entity_registry_sync(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    cloud_prefs: CloudPreferences,
) -> None:
    """Test Google config responds to entity registry."""

    # Enable exposing new entities to Google
    expose_new(menuai, True)

    config = CloudGoogleConfig(
        menuai, GACTIONS_SCHEMA({}), "mock-user-id", cloud_prefs, menuai.data[DATA_CLOUD]
    )
    await config.async_initialize()
    await config.async_connect_agent_user("mock-user-id")

    with (
        patch.object(config, "async_schedule_google_sync_all") as mock_sync,
        patch.object(config, "async_sync_entities_all"),
        patch.object(ga_helpers, "SYNC_DELAY", 0),
    ):
        # Created entity
        entry = entity_registry.async_get_or_create(
            "light", "test", "unique", suggested_object_id="kitchen"
        )
        await menuai.async_block_till_done()

        assert len(mock_sync.mock_calls) == 1

        # Removed entity
        menuai.bus.async_fire(
            er.EVENT_ENTITY_REGISTRY_UPDATED,
            {"action": "remove", "entity_id": entry.entity_id},
        )
        await menuai.async_block_till_done()

        assert len(mock_sync.mock_calls) == 2

        # Entity registry updated with relevant changes
        menuai.bus.async_fire(
            er.EVENT_ENTITY_REGISTRY_UPDATED,
            {
                "action": "update",
                "entity_id": entry.entity_id,
                "changes": ["entity_id"],
            },
        )
        await menuai.async_block_till_done()

        assert len(mock_sync.mock_calls) == 3

        # Entity registry updated with non-relevant changes
        menuai.bus.async_fire(
            er.EVENT_ENTITY_REGISTRY_UPDATED,
            {"action": "update", "entity_id": entry.entity_id, "changes": ["icon"]},
        )
        await menuai.async_block_till_done()

        assert len(mock_sync.mock_calls) == 3

        # When menuai is not started yet we wait till started
        menuai.set_state(CoreState.starting)
        menuai.bus.async_fire(
            er.EVENT_ENTITY_REGISTRY_UPDATED,
            {"action": "create", "entity_id": entry.entity_id},
        )
        await menuai.async_block_till_done()

        assert len(mock_sync.mock_calls) == 3


@pytest.mark.usefixtures("mock_cloud_login")
async def test_google_device_registry_sync(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    cloud_prefs: CloudPreferences,
) -> None:
    """Test Google config responds to device registry."""
    config = CloudGoogleConfig(
        menuai, GACTIONS_SCHEMA({}), "mock-user-id", cloud_prefs, menuai.data[DATA_CLOUD]
    )

    # Enable exposing new entities to Google
    expose_new(menuai, True)

    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entity_entry = entity_registry.async_get_or_create(
        "light", "hue", "1234", device_id=device_entry.id
    )
    entity_entry = entity_registry.async_update_entity(
        entity_entry.entity_id, area_id="ABCD"
    )

    with patch.object(config, "async_sync_entities_all"):
        await config.async_initialize()
        await menuai.async_block_till_done()
        await config.async_connect_agent_user("mock-user-id")
        await menuai.async_block_till_done()

    with patch.object(config, "async_schedule_google_sync_all") as mock_sync:
        # Device registry updated with non-relevant changes
        menuai.bus.async_fire(
            dr.EVENT_DEVICE_REGISTRY_UPDATED,
            {
                "action": "update",
                "device_id": device_entry.id,
                "changes": ["manufacturer"],
            },
        )
        await menuai.async_block_till_done()

        assert len(mock_sync.mock_calls) == 0

        # Device registry updated with relevant changes
        # but entity has area ID so not impacted
        menuai.bus.async_fire(
            dr.EVENT_DEVICE_REGISTRY_UPDATED,
            {
                "action": "update",
                "device_id": device_entry.id,
                "changes": ["area_id"],
            },
        )
        await menuai.async_block_till_done()

        assert len(mock_sync.mock_calls) == 0

        entity_registry.async_update_entity(entity_entry.entity_id, area_id=None)

        # Device registry updated with relevant changes
        # but entity has area ID so not impacted
        menuai.bus.async_fire(
            dr.EVENT_DEVICE_REGISTRY_UPDATED,
            {
                "action": "update",
                "device_id": device_entry.id,
                "changes": ["area_id"],
            },
        )
        await menuai.async_block_till_done()

        assert len(mock_sync.mock_calls) == 1


@pytest.mark.usefixtures("mock_cloud_login")
async def test_sync_google_when_started(
    menuai: menuai, cloud_prefs: CloudPreferences
) -> None:
    """Test Google config syncs on init."""
    config = CloudGoogleConfig(
        menuai, GACTIONS_SCHEMA({}), "mock-user-id", cloud_prefs, menuai.data[DATA_CLOUD]
    )
    with patch.object(config, "async_sync_entities_all") as mock_sync:
        await config.async_initialize()
        await menuai.async_block_till_done()
        assert len(mock_sync.mock_calls) == 1


@pytest.mark.usefixtures("mock_cloud_login")
async def test_sync_google_on_home_assistant_start(
    menuai: menuai, cloud_prefs: CloudPreferences
) -> None:
    """Test Google config syncs when MenuAI started."""
    config = CloudGoogleConfig(
        menuai, GACTIONS_SCHEMA({}), "mock-user-id", cloud_prefs, menuai.data[DATA_CLOUD]
    )
    menuai.set_state(CoreState.not_running)
    with patch.object(config, "async_sync_entities_all") as mock_sync:
        await config.async_initialize()
        await menuai.async_block_till_done()
        assert len(mock_sync.mock_calls) == 0

        menuai.bus.async_fire(EVENT_menuai_START)
        await menuai.async_block_till_done()
        assert len(mock_sync.mock_calls) == 1


async def test_google_config_expose_entity_prefs(
    menuai: menuai,
    mock_conf: CloudGoogleConfig,
    cloud_prefs: CloudPreferences,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test Google config should expose using prefs."""
    assert await async_setup_component(menuai, "menuai", {})
    entity_entry1 = entity_registry.async_get_or_create(
        "light",
        "test",
        "light_config_id",
        suggested_object_id="config_light",
        entity_category=EntityCategory.CONFIG,
    )
    entity_entry2 = entity_registry.async_get_or_create(
        "light",
        "test",
        "light_diagnostic_id",
        suggested_object_id="diagnostic_light",
        entity_category=EntityCategory.DIAGNOSTIC,
    )
    entity_entry3 = entity_registry.async_get_or_create(
        "light",
        "test",
        "light_hidden_integration_id",
        suggested_object_id="hidden_integration_light",
        hidden_by=er.RegistryEntryHider.INTEGRATION,
    )
    entity_entry4 = entity_registry.async_get_or_create(
        "light",
        "test",
        "light_hidden_user_id",
        suggested_object_id="hidden_user_light",
        hidden_by=er.RegistryEntryHider.USER,
    )
    entity_entry5 = entity_registry.async_get_or_create(
        "light",
        "test",
        "light_basement_id",
        suggested_object_id="basement",
    )
    entity_entry6 = entity_registry.async_get_or_create(
        "light",
        "test",
        "light_entrance_id",
        suggested_object_id="entrance",
    )

    expose_new(menuai, True)
    expose_entity(menuai, entity_entry5.entity_id, False)

    state = State("light.kitchen", "on")
    state_config = State(entity_entry1.entity_id, "on")
    state_diagnostic = State(entity_entry2.entity_id, "on")
    state_hidden_integration = State(entity_entry3.entity_id, "on")
    state_hidden_user = State(entity_entry4.entity_id, "on")
    state_not_exposed = State(entity_entry5.entity_id, "on")
    state_exposed_default = State(entity_entry6.entity_id, "on")

    # an entity which is not in the entity registry can be exposed
    expose_entity(menuai, "light.kitchen", True)
    assert mock_conf.should_expose(state)
    # categorized and hidden entities should not be exposed
    assert not mock_conf.should_expose(state_config)
    assert not mock_conf.should_expose(state_diagnostic)
    assert not mock_conf.should_expose(state_hidden_integration)
    assert not mock_conf.should_expose(state_hidden_user)
    # this has been hidden
    assert not mock_conf.should_expose(state_not_exposed)
    # exposed by default
    assert mock_conf.should_expose(state_exposed_default)

    expose_entity(menuai, entity_entry5.entity_id, True)
    assert mock_conf.should_expose(state_not_exposed)

    expose_entity(menuai, entity_entry5.entity_id, None)
    assert not mock_conf.should_expose(state_not_exposed)


@pytest.mark.usefixtures("mock_expired_cloud_login")
def test_enabled_requires_valid_sub(
    menuai: menuai, cloud_prefs: CloudPreferences
) -> None:
    """Test that google config enabled requires a valid Cloud sub."""
    assert cloud_prefs.google_enabled
    assert menuai.data[DATA_CLOUD].is_logged_in
    assert menuai.data[DATA_CLOUD].subscription_expired

    config = CloudGoogleConfig(
        menuai, GACTIONS_SCHEMA({}), "mock-user-id", cloud_prefs, menuai.data[DATA_CLOUD]
    )

    assert not config.enabled


async def test_setup_google_assistant(
    menuai: menuai, mock_conf: CloudGoogleConfig, cloud_prefs: CloudPreferences
) -> None:
    """Test that we set up the google_assistant integration if enabled in cloud."""
    assert await async_setup_component(menuai, "menuai", {})
    mock_conf._cloud.subscription_expired = False

    assert "google_assistant" not in menuai.config.components

    await mock_conf.async_initialize()
    await menuai.async_block_till_done()
    assert "google_assistant" in menuai.config.components

    menuai.config.components.remove("google_assistant")

    await cloud_prefs.async_update()
    await menuai.async_block_till_done()
    assert "google_assistant" in menuai.config.components


@pytest.mark.usefixtures("mock_cloud_login")
async def test_google_handle_logout(
    menuai: menuai, cloud_prefs: CloudPreferences
) -> None:
    """Test Google config responds to logging out."""
    gconf = CloudGoogleConfig(
        menuai, GACTIONS_SCHEMA({}), "mock-user-id", cloud_prefs, Mock(is_logged_in=False)
    )

    await gconf.async_initialize()

    with patch(
        "menuai.components.google_assistant.report_state.async_enable_report_state",
    ) as mock_enable:
        gconf.async_enable_report_state()
        await menuai.async_block_till_done()

    assert len(mock_enable.mock_calls) == 1
    assert len(gconf._on_deinitialize) == 6

    # This will trigger a prefs update when we logout.
    await cloud_prefs.get_cloud_user()

    with patch.object(
        menuai.data[DATA_CLOUD].auth,
        "async_check_token",
        side_effect=AssertionError("Should not be called"),
    ):
        # Fake logging out; CloudClient.logout_cleanups sets username to None
        # and deinitializes the Google config.
        await cloud_prefs.async_set_username(None)
        gconf.async_deinitialize()
        await menuai.async_block_till_done()
        # Check listeners are removed:
        assert not gconf._on_deinitialize

    assert len(mock_enable.return_value.mock_calls) == 1


@pytest.mark.parametrize("google_settings_version", [1, 2])
async def test_google_config_migrate_expose_entity_prefs(
    menuai: menuai,
    cloud_prefs: CloudPreferences,
    entity_registry: er.EntityRegistry,
    google_settings_version: int,
) -> None:
    """Test migrating Google entity config."""
    menuai.set_state(CoreState.not_running)

    assert await async_setup_component(menuai, "menuai", {})
    menuai.states.async_set("light.state_only", "on")
    entity_exposed = entity_registry.async_get_or_create(
        "light",
        "test",
        "light_exposed",
        suggested_object_id="exposed",
    )

    entity_no_2fa_exposed = entity_registry.async_get_or_create(
        "light",
        "test",
        "light_no_2fa_exposed",
        suggested_object_id="no_2fa_exposed",
    )

    entity_migrated = entity_registry.async_get_or_create(
        "light",
        "test",
        "light_migrated",
        suggested_object_id="migrated",
    )

    entity_config = entity_registry.async_get_or_create(
        "light",
        "test",
        "light_config",
        suggested_object_id="config",
        entity_category=EntityCategory.CONFIG,
    )

    entity_default = entity_registry.async_get_or_create(
        "light",
        "test",
        "light_default",
        suggested_object_id="default",
    )

    entity_blocked = entity_registry.async_get_or_create(
        "group",
        "test",
        "group_all_locks",
        suggested_object_id="all_locks",
    )
    assert entity_blocked.entity_id == "group.all_locks"

    await cloud_prefs.async_update(
        google_enabled=True,
        google_report_state=False,
        google_settings_version=google_settings_version,
    )
    expose_entity(menuai, entity_migrated.entity_id, False)

    cloud_prefs._prefs[PREF_GOOGLE_ENTITY_CONFIGS]["light.unknown"] = {
        PREF_SHOULD_EXPOSE: True,
        PREF_DISABLE_2FA: True,
    }
    cloud_prefs._prefs[PREF_GOOGLE_ENTITY_CONFIGS]["light.state_only"] = {
        PREF_SHOULD_EXPOSE: False
    }
    cloud_prefs._prefs[PREF_GOOGLE_ENTITY_CONFIGS][entity_exposed.entity_id] = {
        PREF_SHOULD_EXPOSE: True
    }
    cloud_prefs._prefs[PREF_GOOGLE_ENTITY_CONFIGS][entity_no_2fa_exposed.entity_id] = {
        PREF_SHOULD_EXPOSE: True,
        PREF_DISABLE_2FA: True,
    }
    cloud_prefs._prefs[PREF_GOOGLE_ENTITY_CONFIGS][entity_migrated.entity_id] = {
        PREF_SHOULD_EXPOSE: True
    }
    conf = CloudGoogleConfig(
        menuai, GACTIONS_SCHEMA({}), "mock-user-id", cloud_prefs, Mock(is_logged_in=False)
    )
    await conf.async_initialize()
    menuai.bus.async_fire(EVENT_menuai_START)
    await menuai.async_block_till_done()
    menuai.bus.async_fire(EVENT_menuai_STARTED)
    await menuai.async_block_till_done()

    assert async_get_entity_settings(menuai, "light.unknown") == {
        "cloud.google_assistant": {"disable_2fa": True, "should_expose": True}
    }
    assert async_get_entity_settings(menuai, "light.state_only") == {
        "cloud.google_assistant": {"should_expose": False}
    }
    assert async_get_entity_settings(menuai, entity_exposed.entity_id) == {
        "cloud.google_assistant": {"should_expose": True}
    }
    assert async_get_entity_settings(menuai, entity_migrated.entity_id) == {
        "cloud.google_assistant": {"should_expose": True}
    }
    assert async_get_entity_settings(menuai, entity_no_2fa_exposed.entity_id) == {
        "cloud.google_assistant": {"disable_2fa": True, "should_expose": True}
    }
    assert async_get_entity_settings(menuai, entity_config.entity_id) == {
        "cloud.google_assistant": {"should_expose": False}
    }
    assert async_get_entity_settings(menuai, entity_default.entity_id) == {
        "cloud.google_assistant": {"should_expose": True}
    }
    assert async_get_entity_settings(menuai, entity_blocked.entity_id) == {
        "cloud.google_assistant": {"should_expose": False}
    }


async def test_google_config_migrate_expose_entity_prefs_v2_no_exposed(
    menuai: menuai,
    cloud_prefs: CloudPreferences,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test migrating Google entity config from v2 to v3 when no entity is exposed."""
    menuai.set_state(CoreState.not_running)

    assert await async_setup_component(menuai, "menuai", {})
    menuai.states.async_set("light.state_only", "on")
    entity_migrated = entity_registry.async_get_or_create(
        "light",
        "test",
        "light_migrated",
        suggested_object_id="migrated",
    )
    await cloud_prefs.async_update(
        google_enabled=True,
        google_report_state=False,
        google_settings_version=2,
    )
    expose_entity(menuai, "light.state_only", False)
    expose_entity(menuai, entity_migrated.entity_id, False)

    cloud_prefs._prefs[PREF_GOOGLE_ENTITY_CONFIGS]["light.state_only"] = {
        PREF_SHOULD_EXPOSE: True
    }
    cloud_prefs._prefs[PREF_GOOGLE_ENTITY_CONFIGS][entity_migrated.entity_id] = {
        PREF_SHOULD_EXPOSE: True
    }
    conf = CloudGoogleConfig(
        menuai, GACTIONS_SCHEMA({}), "mock-user-id", cloud_prefs, Mock(is_logged_in=False)
    )
    await conf.async_initialize()
    menuai.bus.async_fire(EVENT_menuai_START)
    await menuai.async_block_till_done()
    menuai.bus.async_fire(EVENT_menuai_STARTED)
    await menuai.async_block_till_done()

    assert async_get_entity_settings(menuai, "light.state_only") == {
        "cloud.google_assistant": {"should_expose": True}
    }
    assert async_get_entity_settings(menuai, entity_migrated.entity_id) == {
        "cloud.google_assistant": {"should_expose": True}
    }


async def test_google_config_migrate_expose_entity_prefs_v2_exposed(
    menuai: menuai,
    cloud_prefs: CloudPreferences,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test migrating Google entity config from v2 to v3 when an entity is exposed."""
    menuai.set_state(CoreState.not_running)

    assert await async_setup_component(menuai, "menuai", {})
    menuai.states.async_set("light.state_only", "on")
    entity_migrated = entity_registry.async_get_or_create(
        "light",
        "test",
        "light_migrated",
        suggested_object_id="migrated",
    )
    await cloud_prefs.async_update(
        google_enabled=True,
        google_report_state=False,
        google_settings_version=2,
    )
    expose_entity(menuai, "light.state_only", False)
    expose_entity(menuai, entity_migrated.entity_id, True)

    cloud_prefs._prefs[PREF_GOOGLE_ENTITY_CONFIGS]["light.state_only"] = {
        PREF_SHOULD_EXPOSE: True
    }
    cloud_prefs._prefs[PREF_GOOGLE_ENTITY_CONFIGS][entity_migrated.entity_id] = {
        PREF_SHOULD_EXPOSE: True
    }
    conf = CloudGoogleConfig(
        menuai, GACTIONS_SCHEMA({}), "mock-user-id", cloud_prefs, Mock(is_logged_in=False)
    )
    await conf.async_initialize()
    menuai.bus.async_fire(EVENT_menuai_START)
    await menuai.async_block_till_done()
    menuai.bus.async_fire(EVENT_menuai_STARTED)
    await menuai.async_block_till_done()

    assert async_get_entity_settings(menuai, "light.state_only") == {
        "cloud.google_assistant": {"should_expose": False}
    }
    assert async_get_entity_settings(menuai, entity_migrated.entity_id) == {
        "cloud.google_assistant": {"should_expose": True}
    }


async def test_google_config_migrate_expose_entity_prefs_default_none(
    menuai: menuai,
    cloud_prefs: CloudPreferences,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test migrating Google entity config."""
    menuai.set_state(CoreState.not_running)

    assert await async_setup_component(menuai, "menuai", {})
    entity_default = entity_registry.async_get_or_create(
        "light",
        "test",
        "light_default",
        suggested_object_id="default",
    )

    await cloud_prefs.async_update(
        google_enabled=True,
        google_report_state=False,
        google_settings_version=1,
    )

    cloud_prefs._prefs[PREF_GOOGLE_DEFAULT_EXPOSE] = None
    conf = CloudGoogleConfig(
        menuai, GACTIONS_SCHEMA({}), "mock-user-id", cloud_prefs, Mock(is_logged_in=False)
    )
    await conf.async_initialize()
    menuai.bus.async_fire(EVENT_menuai_START)
    await menuai.async_block_till_done()
    menuai.bus.async_fire(EVENT_menuai_STARTED)
    await menuai.async_block_till_done()

    assert async_get_entity_settings(menuai, entity_default.entity_id) == {
        "cloud.google_assistant": {"should_expose": True}
    }


async def test_google_config_migrate_expose_entity_prefs_default(
    menuai: menuai,
    cloud_prefs: CloudPreferences,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test migrating Google entity config."""
    menuai.set_state(CoreState.not_running)

    assert await async_setup_component(menuai, "menuai", {})

    binary_sensor_supported = entity_registry.async_get_or_create(
        "binary_sensor",
        "test",
        "binary_sensor_supported",
        original_device_class="door",
        suggested_object_id="supported",
    )

    binary_sensor_unsupported = entity_registry.async_get_or_create(
        "binary_sensor",
        "test",
        "binary_sensor_unsupported",
        original_device_class="battery",
        suggested_object_id="unsupported",
    )

    light = entity_registry.async_get_or_create(
        "light",
        "test",
        "unique",
        suggested_object_id="light",
    )

    sensor_supported = entity_registry.async_get_or_create(
        "sensor",
        "test",
        "sensor_supported",
        original_device_class="temperature",
        suggested_object_id="supported",
    )

    sensor_unsupported = entity_registry.async_get_or_create(
        "sensor",
        "test",
        "sensor_unsupported",
        original_device_class="battery",
        suggested_object_id="unsupported",
    )

    water_heater = entity_registry.async_get_or_create(
        "water_heater",
        "test",
        "unique",
        suggested_object_id="water_heater",
    )

    await cloud_prefs.async_update(
        google_enabled=True,
        google_report_state=False,
        google_settings_version=1,
    )

    cloud_prefs._prefs[PREF_GOOGLE_DEFAULT_EXPOSE] = [
        "binary_sensor",
        "light",
        "sensor",
        "water_heater",
    ]
    conf = CloudGoogleConfig(
        menuai, GACTIONS_SCHEMA({}), "mock-user-id", cloud_prefs, Mock(is_logged_in=False)
    )
    await conf.async_initialize()
    menuai.bus.async_fire(EVENT_menuai_START)
    await menuai.async_block_till_done()
    menuai.bus.async_fire(EVENT_menuai_STARTED)
    await menuai.async_block_till_done()

    assert async_get_entity_settings(menuai, binary_sensor_supported.entity_id) == {
        "cloud.google_assistant": {"should_expose": True}
    }
    assert async_get_entity_settings(menuai, binary_sensor_unsupported.entity_id) == {
        "cloud.google_assistant": {"should_expose": False}
    }
    assert async_get_entity_settings(menuai, light.entity_id) == {
        "cloud.google_assistant": {"should_expose": True}
    }
    assert async_get_entity_settings(menuai, sensor_supported.entity_id) == {
        "cloud.google_assistant": {"should_expose": True}
    }
    assert async_get_entity_settings(menuai, sensor_unsupported.entity_id) == {
        "cloud.google_assistant": {"should_expose": False}
    }
    assert async_get_entity_settings(menuai, water_heater.entity_id) == {
        "cloud.google_assistant": {"should_expose": False}
    }


@pytest.mark.usefixtures("mock_cloud_login")
async def test_google_config_get_agent_user_id(
    menuai: menuai, cloud_prefs: CloudPreferences
) -> None:
    """Test overridden get_agent_user_id_from_webhook method."""
    config = CloudGoogleConfig(
        menuai, GACTIONS_SCHEMA({}), "mock-user-id", cloud_prefs, menuai.data[DATA_CLOUD]
    )
    assert (
        config.get_agent_user_id_from_webhook(cloud_prefs.google_local_webhook_id)
        == config.agent_user_id
    )
    assert config.get_agent_user_id_from_webhook("other_id") != config.agent_user_id


@pytest.mark.usefixtures("mock_cloud_login")
async def test_google_config_get_agent_users(
    menuai: menuai, cloud_prefs: CloudPreferences
) -> None:
    """Test overridden async_get_agent_users method."""
    username_mock = PropertyMock(return_value="blah")

    # We should not call Cloud.username when not logged in
    cloud_prefs._prefs["google_connected"] = True
    assert cloud_prefs.google_connected
    mock_cloud = Mock(is_logged_in=False)
    type(mock_cloud).username = username_mock
    config = CloudGoogleConfig(
        menuai, GACTIONS_SCHEMA({}), "mock-user-id", cloud_prefs, mock_cloud
    )
    assert config.async_get_agent_users() == ()
    username_mock.assert_not_called()

    # We should not call Cloud.username when not connected
    cloud_prefs._prefs["google_connected"] = False
    assert not cloud_prefs.google_connected
    mock_cloud = Mock(is_logged_in=True)
    type(mock_cloud).username = username_mock
    config = CloudGoogleConfig(
        menuai, GACTIONS_SCHEMA({}), "mock-user-id", cloud_prefs, mock_cloud
    )
    assert config.async_get_agent_users() == ()
    username_mock.assert_not_called()

    # Logged in and connected
    cloud_prefs._prefs["google_connected"] = True
    assert cloud_prefs.google_connected
    mock_cloud = Mock(is_logged_in=True)
    type(mock_cloud).username = username_mock
    config = CloudGoogleConfig(
        menuai, GACTIONS_SCHEMA({}), "mock-user-id", cloud_prefs, mock_cloud
    )
    assert config.async_get_agent_users() == ("blah",)
    username_mock.assert_called()
