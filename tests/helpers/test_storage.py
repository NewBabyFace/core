"""Tests for the storage helper."""

import asyncio
from datetime import timedelta
import json
import os
from typing import Any, NamedTuple
from unittest.mock import Mock, patch

from freezegun.api import FrozenDateTimeFactory
import py
import pytest

from menuai.const import (
    EVENT_menuai_FINAL_WRITE,
    EVENT_menuai_START,
    EVENT_menuai_STARTED,
    EVENT_menuai_STOP,
)
from menuai.core import DOMAIN as menuai_DOMAIN, CoreState, menuai
from menuai.exceptions import menuaiError
from menuai.helpers import issue_registry as ir, storage
from menuai.helpers.json import json_bytes
from menuai.util import dt as dt_util
from menuai.util.color import RGBColor

from tests.common import (
    async_fire_time_changed,
    async_fire_time_changed_exact,
    async_test_home_assistant,
)

MOCK_VERSION = 1
MOCK_VERSION_2 = 2
MOCK_MINOR_VERSION_1 = 1
MOCK_MINOR_VERSION_2 = 2
MOCK_KEY = "storage-test"
MOCK_DATA = {"hello": "world"}
MOCK_DATA2 = {"goodbye": "cruel world"}


@pytest.fixture
def store(menuai: menuai) -> storage.Store:
    """Fixture of a store that prevents writing on MenuAI stop."""
    return storage.Store(menuai, MOCK_VERSION, MOCK_KEY)


@pytest.fixture
def store_v_1_1(menuai: menuai) -> storage.Store:
    """Fixture of a store that prevents writing on MenuAI stop."""
    return storage.Store(
        menuai, MOCK_VERSION, MOCK_KEY, minor_version=MOCK_MINOR_VERSION_1
    )


@pytest.fixture
def store_v_1_2(menuai: menuai) -> storage.Store:
    """Fixture of a store that prevents writing on MenuAI stop."""
    return storage.Store(
        menuai, MOCK_VERSION, MOCK_KEY, minor_version=MOCK_MINOR_VERSION_2
    )


@pytest.fixture
def store_v_2_1(menuai: menuai) -> storage.Store:
    """Fixture of a store that prevents writing on MenuAI stop."""
    return storage.Store(
        menuai, MOCK_VERSION_2, MOCK_KEY, minor_version=MOCK_MINOR_VERSION_1
    )


@pytest.fixture
def read_only_store(menuai: menuai) -> storage.Store:
    """Fixture of a read only store."""
    return storage.Store(menuai, MOCK_VERSION, MOCK_KEY, read_only=True)


async def test_loading(menuai: menuai, store: storage.Store) -> None:
    """Test we can save and load data."""
    await store.async_save(MOCK_DATA)
    data = await store.async_load()
    assert data == MOCK_DATA


async def test_custom_encoder(menuai: menuai) -> None:
    """Test we can save and load data."""

    class JSONEncoder(json.JSONEncoder):
        """Mock JSON encoder."""

        def default(self, o):
            """Mock JSON encode method."""
            return "9"

    store = storage.Store(menuai, MOCK_VERSION, MOCK_KEY, encoder=JSONEncoder)
    with pytest.raises(TypeError):
        await store.async_save(Mock())
    await store.async_save(object())
    data = await store.async_load()
    assert data == "9"


async def test_loading_non_existing(menuai: menuai, store: storage.Store) -> None:
    """Test we can save and load data."""
    with patch("menuai.util.json.open", side_effect=FileNotFoundError):
        data = await store.async_load()
    assert data is None


async def test_loading_parallel(
    menuai: menuai,
    store: storage.Store,
    menuai_storage: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test we can save and load data."""
    menuai_storage[store.key] = {"version": MOCK_VERSION, "data": MOCK_DATA}

    results = await asyncio.gather(store.async_load(), store.async_load())

    assert results[0] == MOCK_DATA
    assert results[1] == MOCK_DATA
    assert caplog.text.count(f"Loading data for {store.key}")


async def test_saving_with_delay(
    menuai: menuai, store: storage.Store, menuai_storage: dict[str, Any]
) -> None:
    """Test saving data after a delay."""
    store.async_delay_save(lambda: MOCK_DATA, 1)
    assert store.key not in menuai_storage

    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=1))
    await menuai.async_block_till_done()
    assert menuai_storage[store.key] == {
        "version": MOCK_VERSION,
        "minor_version": 1,
        "key": MOCK_KEY,
        "data": MOCK_DATA,
    }


async def test_saving_with_delay_churn_reduction(
    menuai: menuai,
    store: storage.Store,
    menuai_storage: dict[str, Any],
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test saving data after a delay with timer churn reduction."""
    store.async_delay_save(lambda: MOCK_DATA, 1)
    assert store.key not in menuai_storage

    freezer.tick(0.2)
    async_fire_time_changed_exact(menuai)
    await menuai.async_block_till_done()
    assert store.key not in menuai_storage

    freezer.tick(1)
    async_fire_time_changed_exact(menuai)
    await menuai.async_block_till_done()
    assert menuai_storage[store.key] == {
        "version": MOCK_VERSION,
        "minor_version": 1,
        "key": MOCK_KEY,
        "data": MOCK_DATA,
    }

    del menuai_storage[store.key]
    # Simulate what some of the registries do when they add 100 entities
    for _ in range(100):
        store.async_delay_save(lambda: MOCK_DATA, 1)

    freezer.tick(0.2)
    async_fire_time_changed_exact(menuai)
    await menuai.async_block_till_done()
    assert store.key not in menuai_storage
    store.async_delay_save(lambda: MOCK_DATA, 1)

    freezer.tick(1)
    async_fire_time_changed_exact(menuai)
    await menuai.async_block_till_done()
    assert store.key in menuai_storage

    del menuai_storage[store.key]

    store.async_delay_save(lambda: MOCK_DATA, 1)
    freezer.tick(0.5)
    async_fire_time_changed_exact(menuai)
    await menuai.async_block_till_done()
    assert store.key not in menuai_storage

    store.async_delay_save(lambda: MOCK_DATA, 1)
    freezer.tick(0.8)
    async_fire_time_changed_exact(menuai)
    await menuai.async_block_till_done()
    assert store.key not in menuai_storage

    store.async_delay_save(lambda: MOCK_DATA, 1)
    freezer.tick(0.8)
    async_fire_time_changed_exact(menuai)
    await menuai.async_block_till_done()
    assert store.key not in menuai_storage

    freezer.tick(0.2)
    async_fire_time_changed_exact(menuai)
    await menuai.async_block_till_done()
    assert store.key in menuai_storage

    # Make sure if we do another delayed save
    # and one with a shorter delay, the shorter delay wins
    del menuai_storage[store.key]
    store.async_delay_save(lambda: MOCK_DATA, 2)
    freezer.tick(0.2)
    async_fire_time_changed_exact(menuai)
    await menuai.async_block_till_done()
    assert store.key not in menuai_storage

    store.async_delay_save(lambda: MOCK_DATA, 1)
    freezer.tick(1.0)
    async_fire_time_changed_exact(menuai)
    await menuai.async_block_till_done()
    assert store.key in menuai_storage


async def test_saving_on_final_write(
    menuai: menuai, menuai_storage: dict[str, Any]
) -> None:
    """Test delayed saves trigger when we quit MenuAI."""
    store = storage.Store(menuai, MOCK_VERSION, MOCK_KEY)
    store.async_delay_save(lambda: MOCK_DATA, 5)
    assert store.key not in menuai_storage

    menuai.bus.async_fire(EVENT_menuai_STOP)
    menuai.set_state(CoreState.stopping)
    await menuai.async_block_till_done()

    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=10))
    await menuai.async_block_till_done()
    assert store.key not in menuai_storage

    menuai.bus.async_fire(EVENT_menuai_FINAL_WRITE)
    await menuai.async_block_till_done()
    assert menuai_storage[store.key] == {
        "version": MOCK_VERSION,
        "minor_version": 1,
        "key": MOCK_KEY,
        "data": MOCK_DATA,
    }


async def test_not_delayed_saving_while_stopping(
    menuai: menuai, menuai_storage: dict[str, Any]
) -> None:
    """Test delayed saves don't write after the stop event has fired."""
    store = storage.Store(menuai, MOCK_VERSION, MOCK_KEY)
    menuai.bus.async_fire(EVENT_menuai_STOP)
    await menuai.async_block_till_done()
    menuai.set_state(CoreState.stopping)

    store.async_delay_save(lambda: MOCK_DATA, 1)
    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=2))
    await menuai.async_block_till_done()
    assert store.key not in menuai_storage


async def test_not_delayed_saving_after_stopping(
    menuai: menuai, menuai_storage: dict[str, Any]
) -> None:
    """Test delayed saves don't write after stop if issued before stopping MenuAI."""
    store = storage.Store(menuai, MOCK_VERSION, MOCK_KEY)
    store.async_delay_save(lambda: MOCK_DATA, 10)
    assert store.key not in menuai_storage

    menuai.bus.async_fire(EVENT_menuai_STOP)
    menuai.set_state(CoreState.stopping)
    await menuai.async_block_till_done()
    assert store.key not in menuai_storage

    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=15))
    await menuai.async_block_till_done()
    assert store.key not in menuai_storage


async def test_not_saving_while_stopping(
    menuai: menuai, menuai_storage: dict[str, Any]
) -> None:
    """Test saves don't write when stopping MenuAI."""
    store = storage.Store(menuai, MOCK_VERSION, MOCK_KEY)
    menuai.set_state(CoreState.stopping)
    await store.async_save(MOCK_DATA)
    assert store.key not in menuai_storage


async def test_loading_while_delay(
    menuai: menuai, store: storage.Store, menuai_storage: dict[str, Any]
) -> None:
    """Test we load new data even if not written yet."""
    await store.async_save({"delay": "no"})
    assert menuai_storage[store.key] == {
        "version": MOCK_VERSION,
        "minor_version": 1,
        "key": MOCK_KEY,
        "data": {"delay": "no"},
    }

    store.async_delay_save(lambda: {"delay": "yes"}, 1)
    assert menuai_storage[store.key] == {
        "version": MOCK_VERSION,
        "minor_version": 1,
        "key": MOCK_KEY,
        "data": {"delay": "no"},
    }

    data = await store.async_load()
    assert data == {"delay": "yes"}


async def test_writing_while_writing_delay(
    menuai: menuai, store: storage.Store, menuai_storage: dict[str, Any]
) -> None:
    """Test a write while a write with delay is active."""
    store.async_delay_save(lambda: {"delay": "yes"}, 1)
    assert store.key not in menuai_storage
    await store.async_save({"delay": "no"})
    assert menuai_storage[store.key] == {
        "version": MOCK_VERSION,
        "minor_version": 1,
        "key": MOCK_KEY,
        "data": {"delay": "no"},
    }

    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=1))
    await menuai.async_block_till_done()
    assert menuai_storage[store.key] == {
        "version": MOCK_VERSION,
        "minor_version": 1,
        "key": MOCK_KEY,
        "data": {"delay": "no"},
    }

    data = await store.async_load()
    assert data == {"delay": "no"}


async def test_multiple_delay_save_calls(
    menuai: menuai, store: storage.Store, menuai_storage: dict[str, Any]
) -> None:
    """Test a write while a write with changing delays."""
    store.async_delay_save(lambda: {"delay": "yes"}, 1)
    store.async_delay_save(lambda: {"delay": "yes"}, 2)
    store.async_delay_save(lambda: {"delay": "yes"}, 3)

    assert store.key not in menuai_storage
    await store.async_save({"delay": "no"})
    assert menuai_storage[store.key] == {
        "version": MOCK_VERSION,
        "minor_version": 1,
        "key": MOCK_KEY,
        "data": {"delay": "no"},
    }

    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=1))
    await menuai.async_block_till_done()
    assert menuai_storage[store.key] == {
        "version": MOCK_VERSION,
        "minor_version": 1,
        "key": MOCK_KEY,
        "data": {"delay": "no"},
    }

    data = await store.async_load()
    assert data == {"delay": "no"}


async def test_delay_save_zero(
    menuai: menuai, store: storage.Store, menuai_storage: dict[str, Any]
) -> None:
    """Test async_delay_save accepts 0."""
    store.async_delay_save(lambda: {"delay": "0"}, 0)
    # sleep is to run one event loop to get the task scheduled
    await asyncio.sleep(0)
    await menuai.async_block_till_done()
    assert store.key in menuai_storage
    assert menuai_storage[store.key] == {
        "version": MOCK_VERSION,
        "minor_version": 1,
        "key": MOCK_KEY,
        "data": {"delay": "0"},
    }


async def test_multiple_save_calls(
    menuai: menuai, store: storage.Store, menuai_storage: dict[str, Any]
) -> None:
    """Test multiple write tasks."""

    assert store.key not in menuai_storage

    tasks = [store.async_save({"savecount": savecount}) for savecount in range(6)]
    await asyncio.gather(*tasks)
    assert menuai_storage[store.key] == {
        "version": MOCK_VERSION,
        "minor_version": 1,
        "key": MOCK_KEY,
        "data": {"savecount": 5},
    }

    data = await store.async_load()
    assert data == {"savecount": 5}


async def test_migrator_no_existing_config(
    menuai: menuai, store: storage.Store, menuai_storage: dict[str, Any]
) -> None:
    """Test migrator with no existing config."""
    with (
        patch("os.path.isfile", return_value=False),
        patch.object(store, "async_load", return_value={"cur": "config"}),
    ):
        data = await storage.async_migrator(menuai, "old-path", store)

    assert data == {"cur": "config"}
    assert store.key not in menuai_storage


async def test_migrator_existing_config(
    menuai: menuai, store: storage.Store, menuai_storage: dict[str, Any]
) -> None:
    """Test migrating existing config."""
    with patch("os.path.isfile", return_value=True), patch("os.remove") as mock_remove:
        data = await storage.async_migrator(
            menuai, "old-path", store, old_conf_load_func=lambda _: {"old": "config"}
        )

    assert len(mock_remove.mock_calls) == 1
    assert data == {"old": "config"}
    assert menuai_storage[store.key] == {
        "key": MOCK_KEY,
        "version": MOCK_VERSION,
        "minor_version": 1,
        "data": data,
    }


async def test_migrator_transforming_config(
    menuai: menuai, store: storage.Store, menuai_storage: dict[str, Any]
) -> None:
    """Test migrating config to new format."""

    async def old_conf_migrate_func(old_config):
        """Migrate old config to new format."""
        return {"new": old_config["old"]}

    with patch("os.path.isfile", return_value=True), patch("os.remove") as mock_remove:
        data = await storage.async_migrator(
            menuai,
            "old-path",
            store,
            old_conf_migrate_func=old_conf_migrate_func,
            old_conf_load_func=lambda _: {"old": "config"},
        )

    assert len(mock_remove.mock_calls) == 1
    assert data == {"new": "config"}
    assert menuai_storage[store.key] == {
        "key": MOCK_KEY,
        "version": MOCK_VERSION,
        "minor_version": 1,
        "data": data,
    }


async def test_minor_version_default(
    menuai: menuai, store: storage.Store, menuai_storage: dict[str, Any]
) -> None:
    """Test minor version default."""

    await store.async_save(MOCK_DATA)
    assert menuai_storage[store.key]["minor_version"] == 1


async def test_minor_version(
    menuai: menuai, store_v_1_2: storage.Store, menuai_storage: dict[str, Any]
) -> None:
    """Test minor version."""

    await store_v_1_2.async_save(MOCK_DATA)
    assert menuai_storage[store_v_1_2.key]["minor_version"] == MOCK_MINOR_VERSION_2


async def test_migrate_major_not_implemented_raises(
    menuai: menuai, store: storage.Store, store_v_2_1: storage.Store
) -> None:
    """Test migrating between major versions fails if not implemented."""

    await store_v_2_1.async_save(MOCK_DATA)
    with pytest.raises(NotImplementedError):
        await store.async_load()


async def test_migrate_minor_not_implemented(
    menuai: menuai,
    menuai_storage: dict[str, Any],
    store_v_1_1: storage.Store,
    store_v_1_2: storage.Store,
) -> None:
    """Test migrating between minor versions does not fail if not implemented."""

    assert store_v_1_1.key == store_v_1_2.key

    await store_v_1_1.async_save(MOCK_DATA)
    assert menuai_storage[store_v_1_1.key] == {
        "key": MOCK_KEY,
        "version": MOCK_VERSION,
        "minor_version": MOCK_MINOR_VERSION_1,
        "data": MOCK_DATA,
    }
    data = await store_v_1_2.async_load()
    assert menuai_storage[store_v_1_1.key]["data"] == data

    await store_v_1_2.async_save(MOCK_DATA)
    assert menuai_storage[store_v_1_2.key] == {
        "key": MOCK_KEY,
        "version": MOCK_VERSION,
        "minor_version": MOCK_MINOR_VERSION_2,
        "data": MOCK_DATA,
    }


async def test_migration(
    menuai: menuai, menuai_storage: dict[str, Any], store_v_1_2: storage.Store
) -> None:
    """Test migration."""
    calls = 0

    class CustomStore(storage.Store):
        async def _async_migrate_func(
            self, old_major_version, old_minor_version, old_data: dict
        ):
            nonlocal calls
            calls += 1
            assert old_major_version == store_v_1_2.version
            assert old_minor_version == store_v_1_2.minor_version
            return old_data

    await store_v_1_2.async_save(MOCK_DATA)
    assert menuai_storage[store_v_1_2.key] == {
        "key": MOCK_KEY,
        "version": MOCK_VERSION,
        "minor_version": MOCK_MINOR_VERSION_2,
        "data": MOCK_DATA,
    }
    assert calls == 0

    custom_store = CustomStore(menuai, 2, store_v_1_2.key, minor_version=1)
    data = await custom_store.async_load()
    assert calls == 1
    assert menuai_storage[store_v_1_2.key]["data"] == data

    # Assert the migrated data has been saved
    assert menuai_storage[custom_store.key] == {
        "key": MOCK_KEY,
        "version": 2,
        "minor_version": 1,
        "data": MOCK_DATA,
    }


async def test_legacy_migration(
    menuai: menuai, menuai_storage: dict[str, Any], store_v_1_2: storage.Store
) -> None:
    """Test legacy migration method signature."""
    calls = 0

    class LegacyStore(storage.Store):
        async def _async_migrate_func(self, old_version, old_data: dict):
            nonlocal calls
            calls += 1
            assert old_version == store_v_1_2.version
            return old_data

    await store_v_1_2.async_save(MOCK_DATA)
    assert menuai_storage[store_v_1_2.key] == {
        "key": MOCK_KEY,
        "version": MOCK_VERSION,
        "minor_version": MOCK_MINOR_VERSION_2,
        "data": MOCK_DATA,
    }
    assert calls == 0

    legacy_store = LegacyStore(menuai, 2, store_v_1_2.key, minor_version=1)
    data = await legacy_store.async_load()
    assert calls == 1
    assert menuai_storage[store_v_1_2.key]["data"] == data

    # Assert the migrated data has been saved
    assert menuai_storage[legacy_store.key] == {
        "key": MOCK_KEY,
        "version": 2,
        "minor_version": 1,
        "data": MOCK_DATA,
    }


async def test_changing_delayed_written_data(
    menuai: menuai, store: storage.Store, menuai_storage: dict[str, Any]
) -> None:
    """Test changing data that is written with delay."""
    data_to_store = {"hello": "world"}
    store.async_delay_save(lambda: data_to_store, 1)
    assert store.key not in menuai_storage

    loaded_data = await store.async_load()
    assert loaded_data == data_to_store
    assert loaded_data is not data_to_store

    loaded_data["hello"] = "earth"

    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=1))
    await menuai.async_block_till_done()
    assert menuai_storage[store.key] == {
        "version": MOCK_VERSION,
        "minor_version": 1,
        "key": MOCK_KEY,
        "data": {"hello": "world"},
    }


async def test_saving_load_round_trip(tmpdir: py.path.local) -> None:
    """Test saving and loading round trip."""
    loop = asyncio.get_running_loop()
    config_dir = await loop.run_in_executor(None, tmpdir.mkdir, "temp_storage")
    async with async_test_home_assistant(config_dir=config_dir.strpath) as menuai:

        class NamedTupleSubclass(NamedTuple):
            """A NamedTuple subclass."""

            name: str

        nts = NamedTupleSubclass("a")

        data = {
            "named_tuple_subclass": nts,
            "rgb_color": RGBColor(255, 255, 0),
            "set": {1, 2, 3},
            "list": [1, 2, 3],
            "tuple": (1, 2, 3),
            "dict_with_int": {1: 1, 2: 2},
            "dict_with_named_tuple": {1: nts, 2: nts},
        }

        store = storage.Store(
            menuai, MOCK_VERSION_2, MOCK_KEY, minor_version=MOCK_MINOR_VERSION_1
        )
        await store.async_save(data)
        load = await store.async_load()
        assert load == {
            "dict_with_int": {"1": 1, "2": 2},
            "dict_with_named_tuple": {"1": ["a"], "2": ["a"]},
            "list": [1, 2, 3],
            "named_tuple_subclass": ["a"],
            "rgb_color": [255, 255, 0],
            "set": [1, 2, 3],
            "tuple": [1, 2, 3],
        }

        await menuai.async_stop(force=True)


async def test_loading_corrupt_core_file(
    tmpdir: py.path.local, caplog: pytest.LogCaptureFixture
) -> None:
    """Test we handle unrecoverable corruption in a core file."""
    loop = asyncio.get_running_loop()
    tmp_storage = await loop.run_in_executor(None, tmpdir.mkdir, "temp_storage")

    async with async_test_home_assistant(config_dir=tmp_storage.strpath) as menuai:
        storage_key = "core.anything"
        store = storage.Store(
            menuai, MOCK_VERSION_2, storage_key, minor_version=MOCK_MINOR_VERSION_1
        )
        await store.async_save({"hello": "world"})
        storage_path = os.path.join(tmp_storage, ".storage")
        store_file = os.path.join(storage_path, store.key)

        data = await store.async_load()
        assert data == {"hello": "world"}

        def _corrupt_store():
            with open(store_file, "w", encoding="utf8") as f:
                f.write("corrupt")

        await menuai.async_add_executor_job(_corrupt_store)

        data = await store.async_load()
        assert data is None
        assert "Unrecoverable error decoding storage" in caplog.text

        issue_registry = ir.async_get(menuai)
        found_issue = None
        issue_entry = None
        for (domain, issue), entry in issue_registry.issues.items():
            if domain == menuai_DOMAIN and issue.startswith(
                f"storage_corruption_{storage_key}_"
            ):
                found_issue = issue
                issue_entry = entry
                break

        assert found_issue is not None
        assert issue_entry is not None
        assert issue_entry.is_fixable is True
        assert issue_entry.translation_placeholders["storage_key"] == storage_key
        assert issue_entry.issue_domain == menuai_DOMAIN
        assert (
            "unexpected character: line 1 column 1 (char 0)"
            in issue_entry.translation_placeholders["error"]
        )

        files = await menuai.async_add_executor_job(
            os.listdir, os.path.join(tmp_storage, ".storage")
        )
        assert ".corrupt" in files[0]

        await menuai.async_stop(force=True)


async def test_loading_corrupt_file_known_domain(
    tmpdir: py.path.local, caplog: pytest.LogCaptureFixture
) -> None:
    """Test we handle unrecoverable corruption for a known domain."""

    loop = asyncio.get_running_loop()
    tmp_storage = await loop.run_in_executor(None, tmpdir.mkdir, "temp_storage")

    async with async_test_home_assistant(config_dir=tmp_storage.strpath) as menuai:
        menuai.config.components.add("testdomain")
        storage_key = "testdomain.testkey"

        store = storage.Store(
            menuai, MOCK_VERSION_2, storage_key, minor_version=MOCK_MINOR_VERSION_1
        )
        await store.async_save({"hello": "world"})
        storage_path = os.path.join(tmp_storage, ".storage")
        store_file = os.path.join(storage_path, store.key)

        data = await store.async_load()
        assert data == {"hello": "world"}

        def _corrupt_store():
            with open(store_file, "w", encoding="utf8") as f:
                f.write('{"valid":"json"}..with..corrupt')

        await menuai.async_add_executor_job(_corrupt_store)

        data = await store.async_load()
        assert data is None
        assert "Unrecoverable error decoding storage" in caplog.text

        issue_registry = ir.async_get(menuai)
        found_issue = None
        issue_entry = None
        for (domain, issue), entry in issue_registry.issues.items():
            if domain == menuai_DOMAIN and issue.startswith(
                f"storage_corruption_{storage_key}_"
            ):
                found_issue = issue
                issue_entry = entry
                break

        assert found_issue is not None
        assert issue_entry is not None
        assert issue_entry.is_fixable is True
        assert issue_entry.translation_placeholders["storage_key"] == storage_key
        assert issue_entry.issue_domain == "testdomain"
        assert (
            "unexpected content after document: line 1 column 17 (char 16)"
            in issue_entry.translation_placeholders["error"]
        )

        files = await menuai.async_add_executor_job(
            os.listdir, os.path.join(tmp_storage, ".storage")
        )
        assert ".corrupt" in files[0]

        await menuai.async_stop(force=True)


async def test_os_error_is_fatal(tmpdir: py.path.local) -> None:
    """Test OSError during load is fatal."""
    loop = asyncio.get_running_loop()
    tmp_storage = await loop.run_in_executor(None, tmpdir.mkdir, "temp_storage")
    async with async_test_home_assistant(config_dir=tmp_storage.strpath) as menuai:
        store = storage.Store(
            menuai, MOCK_VERSION_2, MOCK_KEY, minor_version=MOCK_MINOR_VERSION_1
        )
        await store.async_save({"hello": "world"})

        with (
            pytest.raises(OSError),
            patch(
                "menuai.helpers.storage.json_util.load_json", side_effect=OSError
            ),
        ):
            await store.async_load()

        # Verify second load is also failing
        with (
            pytest.raises(OSError),
            patch(
                "menuai.helpers.storage.json_util.load_json", side_effect=OSError
            ),
        ):
            await store.async_load()

        await menuai.async_stop(force=True)


async def test_json_load_failure(tmpdir: py.path.local) -> None:
    """Test json load raising menuaiError."""
    loop = asyncio.get_running_loop()
    tmp_storage = await loop.run_in_executor(None, tmpdir.mkdir, "temp_storage")
    async with async_test_home_assistant(config_dir=tmp_storage.strpath) as menuai:
        store = storage.Store(
            menuai, MOCK_VERSION_2, MOCK_KEY, minor_version=MOCK_MINOR_VERSION_1
        )
        await store.async_save({"hello": "world"})
        base_os_error = OSError()
        base_os_error.errno = 30
        home_assistant_error = menuaiError()
        home_assistant_error.__cause__ = base_os_error

        with (
            pytest.raises(menuaiError),
            patch(
                "menuai.helpers.storage.json_util.load_json",
                side_effect=home_assistant_error,
            ),
        ):
            await store.async_load()

        await menuai.async_stop(force=True)


async def test_read_only_store(
    menuai: menuai, read_only_store: storage.Store, menuai_storage: dict[str, Any]
) -> None:
    """Test store opened in read only mode does not save."""
    read_only_store.async_delay_save(lambda: MOCK_DATA, 1)
    assert read_only_store.key not in menuai_storage

    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=1))
    await menuai.async_block_till_done()
    assert read_only_store.key not in menuai_storage

    menuai.bus.async_fire(EVENT_menuai_STOP)
    menuai.set_state(CoreState.stopping)
    await menuai.async_block_till_done()

    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=10))
    await menuai.async_block_till_done()
    assert read_only_store.key not in menuai_storage

    menuai.bus.async_fire(EVENT_menuai_FINAL_WRITE)
    await menuai.async_block_till_done()
    assert read_only_store.key not in menuai_storage


async def test_store_manager_caching(
    tmpdir: py.path.local, caplog: pytest.LogCaptureFixture
) -> None:
    """Test store manager caching."""
    loop = asyncio.get_running_loop()

    def _setup_mock_storage():
        config_dir = tmpdir.mkdir("temp_config")
        tmp_storage = config_dir.mkdir(".storage")
        tmp_storage.join("integration1").write_binary(
            json_bytes({"data": {"integration1": "integration1"}, "version": 1})
        )
        tmp_storage.join("integration2").write_binary(
            json_bytes({"data": {"integration2": "integration2"}, "version": 1})
        )
        tmp_storage.join("broken").write_binary(b"invalid")
        return config_dir

    config_dir = await loop.run_in_executor(None, _setup_mock_storage)

    async with async_test_home_assistant(config_dir=config_dir.strpath) as menuai:
        store_manager = storage.get_internal_store_manager(menuai)
        assert (
            store_manager.async_fetch("integration1") is None
        )  # has data but not cached
        assert (
            store_manager.async_fetch("integration2") is None
        )  # has data but not cached
        assert (
            store_manager.async_fetch("integration3") is None
        )  # no file not but cached

        await store_manager.async_initialize()
        assert (
            store_manager.async_fetch("integration1") is None
        )  # has data but not cached
        assert (
            store_manager.async_fetch("integration2") is None
        )  # has data but not cached
        assert (
            store_manager.async_fetch("integration3") is not None
        )  # no file and initialized

        result = store_manager.async_fetch("integration3")
        assert result is not None
        exists, data = result
        assert exists is False
        assert data is None

        await store_manager.async_preload(["integration3", "integration2", "broken"])
        assert "Error loading broken" in caplog.text

        assert (
            store_manager.async_fetch("integration1") is None
        )  # has data but not cached
        result = store_manager.async_fetch("integration2")
        assert result is not None
        exists, data = result
        assert exists is True
        assert data == {"data": {"integration2": "integration2"}, "version": 1}

        assert (
            store_manager.async_fetch("integration3") is not None
        )  # no file and initialized
        result = store_manager.async_fetch("integration3")
        assert result is not None
        exists, data = result
        assert exists is False
        assert data is None

        integration1 = storage.Store(menuai, 1, "integration1")
        await integration1.async_save({"integration1": "updated"})
        # Save should invalidate the cache
        assert store_manager.async_fetch("integration1") is None  # invalidated

        integration2 = storage.Store(menuai, 1, "integration2")
        integration2.async_delay_save(lambda: {"integration2": "updated"})
        # Delay save should invalidate the cache after it saves
        assert "integration2" not in store_manager._invalidated

        # Block twice to flush out the delayed save
        await menuai.async_block_till_done()
        await menuai.async_block_till_done()
        assert store_manager.async_fetch("integration2") is None  # invalidated

        store_manager.async_invalidate("integration3")
        assert store_manager.async_fetch("integration1") is None  # invalidated by save
        assert (
            store_manager.async_fetch("integration2") is None
        )  # invalidated by delay save
        assert store_manager.async_fetch("integration3") is None  # invalidated

        await menuai.async_stop(force=True)

    async with async_test_home_assistant(config_dir=config_dir.strpath) as menuai:
        store_manager = storage.get_internal_store_manager(menuai)
        assert store_manager.async_fetch("integration1") is None
        assert store_manager.async_fetch("integration2") is None
        assert store_manager.async_fetch("integration3") is None
        await store_manager.async_initialize()
        await store_manager.async_preload(["integration1", "integration2"])
        result = store_manager.async_fetch("integration1")
        assert result is not None
        exists, data = result
        assert exists is True
        assert data["data"] == {"integration1": "updated"}

        integration1 = storage.Store(menuai, 1, "integration1")
        assert await integration1.async_load() == {"integration1": "updated"}

        # Load should pop the cache
        assert store_manager.async_fetch("integration1") is None

        integration2 = storage.Store(menuai, 1, "integration2")
        assert await integration2.async_load() == {"integration2": "updated"}

        # Load should pop the cache
        assert store_manager.async_fetch("integration2") is None

        integration3 = storage.Store(menuai, 1, "integration3")
        assert await integration3.async_load() is None

        await integration3.async_save({"integration3": "updated"})
        assert await integration3.async_load() == {"integration3": "updated"}

        await menuai.async_stop(force=True)

    # Now make sure everything still works when we do not
    # manually load the storage manager
    async with async_test_home_assistant(config_dir=config_dir.strpath) as menuai:
        integration1 = storage.Store(menuai, 1, "integration1")
        assert await integration1.async_load() == {"integration1": "updated"}
        await integration1.async_save({"integration1": "updated2"})
        assert await integration1.async_load() == {"integration1": "updated2"}

        integration2 = storage.Store(menuai, 1, "integration2")
        assert await integration2.async_load() == {"integration2": "updated"}
        await integration2.async_save({"integration2": "updated2"})
        assert await integration2.async_load() == {"integration2": "updated2"}

        await menuai.async_stop(force=True)

    # Now remove the stores
    async with async_test_home_assistant(config_dir=config_dir.strpath) as menuai:
        store_manager = storage.get_internal_store_manager(menuai)
        await store_manager.async_initialize()
        await store_manager.async_preload(["integration1", "integration2"])

        integration1 = storage.Store(menuai, 1, "integration1")
        assert integration1._manager is store_manager
        assert await integration1.async_load() == {"integration1": "updated2"}

        integration2 = storage.Store(menuai, 1, "integration2")
        assert integration2._manager is store_manager
        assert await integration2.async_load() == {"integration2": "updated2"}

        await integration1.async_remove()
        await integration2.async_remove()

        assert store_manager.async_fetch("integration1") is None
        assert store_manager.async_fetch("integration2") is None

        assert await integration1.async_load() is None
        assert await integration2.async_load() is None

        await menuai.async_stop(force=True)

    # Now make sure the stores are removed and another run works
    async with async_test_home_assistant(config_dir=config_dir.strpath) as menuai:
        store_manager = storage.get_internal_store_manager(menuai)
        await store_manager.async_initialize()
        await store_manager.async_preload(["integration1"])
        result = store_manager.async_fetch("integration1")
        assert result is not None
        exists, data = result
        assert exists is False
        assert data is None
        await menuai.async_stop(force=True)


async def test_store_manager_sub_dirs(tmpdir: py.path.local) -> None:
    """Test store manager ignores subdirs."""
    loop = asyncio.get_running_loop()

    def _setup_mock_storage():
        config_dir = tmpdir.mkdir("temp_config")
        sub_dir_storage = config_dir.mkdir(".storage").mkdir("subdir")

        sub_dir_storage.join("integration1").write_binary(
            json_bytes({"data": {"integration1": "integration1"}, "version": 1})
        )
        return config_dir

    config_dir = await loop.run_in_executor(None, _setup_mock_storage)

    async with async_test_home_assistant(config_dir=config_dir.strpath) as menuai:
        store_manager = storage.get_internal_store_manager(menuai)
        await store_manager.async_initialize()
        assert store_manager.async_fetch("subdir/integration1") is None
        assert store_manager.async_fetch("subdir/integrationx") is None
        integration1 = storage.Store(menuai, 1, "subdir/integration1")
        assert await integration1.async_load() == {"integration1": "integration1"}
        await menuai.async_stop(force=True)


async def test_store_manager_cleanup_after_started(
    tmpdir: py.path.local, freezer: FrozenDateTimeFactory
) -> None:
    """Test that the cache is cleaned up after startup."""
    loop = asyncio.get_running_loop()

    def _setup_mock_storage():
        config_dir = tmpdir.mkdir("temp_config")
        tmp_storage = config_dir.mkdir(".storage")
        tmp_storage.join("integration1").write_binary(
            json_bytes({"data": {"integration1": "integration1"}, "version": 1})
        )
        tmp_storage.join("integration2").write_binary(
            json_bytes({"data": {"integration2": "integration2"}, "version": 1})
        )
        return config_dir

    config_dir = await loop.run_in_executor(None, _setup_mock_storage)

    async with async_test_home_assistant(config_dir=config_dir.strpath) as menuai:
        menuai.set_state(CoreState.not_running)
        store_manager = storage.get_internal_store_manager(menuai)
        await store_manager.async_initialize()
        await store_manager.async_preload(["integration1", "integration2"])
        assert "integration1" in store_manager._data_preload
        assert "integration2" in store_manager._data_preload
        menuai.bus.async_fire(EVENT_menuai_START)
        await menuai.async_block_till_done()
        assert "integration1" in store_manager._data_preload
        assert "integration2" in store_manager._data_preload
        menuai.bus.async_fire(EVENT_menuai_STARTED)
        await menuai.async_block_till_done()
        assert "integration1" in store_manager._data_preload
        assert "integration2" in store_manager._data_preload
        freezer.tick(storage.MANAGER_CLEANUP_DELAY)
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()
        # The cache should be removed after the cleanup delay
        # since it means nothing ever loaded it and we want to
        # recover the memory
        assert "integration1" not in store_manager._data_preload
        assert "integration2" not in store_manager._data_preload
        assert store_manager.async_fetch("integration1") is None
        assert store_manager.async_fetch("integration2") is None
        await menuai.async_stop(force=True)


async def test_store_manager_cleanup_after_stop(
    tmpdir: py.path.local, freezer: FrozenDateTimeFactory
) -> None:
    """Test that the cache is cleaned up after stop event.

    This should only happen if we stop within the cleanup delay.
    """
    loop = asyncio.get_running_loop()

    def _setup_mock_storage():
        config_dir = tmpdir.mkdir("temp_config")
        tmp_storage = config_dir.mkdir(".storage")
        tmp_storage.join("integration1").write_binary(
            json_bytes({"data": {"integration1": "integration1"}, "version": 1})
        )
        tmp_storage.join("integration2").write_binary(
            json_bytes({"data": {"integration2": "integration2"}, "version": 1})
        )
        return config_dir

    config_dir = await loop.run_in_executor(None, _setup_mock_storage)

    async with async_test_home_assistant(config_dir=config_dir.strpath) as menuai:
        menuai.set_state(CoreState.not_running)
        store_manager = storage.get_internal_store_manager(menuai)
        await store_manager.async_initialize()
        await store_manager.async_preload(["integration1", "integration2"])
        assert "integration1" in store_manager._data_preload
        assert "integration2" in store_manager._data_preload
        menuai.bus.async_fire(EVENT_menuai_START)
        await menuai.async_block_till_done()
        assert "integration1" in store_manager._data_preload
        assert "integration2" in store_manager._data_preload
        menuai.bus.async_fire(EVENT_menuai_STARTED)
        await menuai.async_block_till_done()
        assert "integration1" in store_manager._data_preload
        assert "integration2" in store_manager._data_preload
        menuai.bus.async_fire(EVENT_menuai_STOP)
        await menuai.async_block_till_done()
        assert "integration1" not in store_manager._data_preload
        assert "integration2" not in store_manager._data_preload
        assert store_manager.async_fetch("integration1") is None
        assert store_manager.async_fetch("integration2") is None
        await menuai.async_stop(force=True)


async def test_storage_concurrent_load(menuai: menuai) -> None:
    """Test that we can load the store concurrently."""

    store = storage.Store(menuai, MOCK_VERSION, MOCK_KEY)

    async def _load_store():
        await asyncio.sleep(0)
        return "data"

    with patch.object(store, "_async_load", side_effect=_load_store):
        # Test that we can load the store concurrently
        loads = await asyncio.gather(
            store.async_load(), store.async_load(), store.async_load()
        )
        for load in loads:
            assert load == "data"
