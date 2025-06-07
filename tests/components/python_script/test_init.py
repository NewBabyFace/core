"""Test the python_script component."""

import logging
from unittest.mock import mock_open, patch

import pytest

from menuai.components.python_script import DOMAIN, FOLDER, execute
from menuai.core import menuai
from menuai.exceptions import menuaiError, ServiceValidationError
from menuai.helpers.service import async_get_all_descriptions
from menuai.setup import async_setup_component

from tests.common import patch_yaml_files


async def test_setup(menuai: menuai) -> None:
    """Test we can discover scripts."""
    scripts = [
        "/some/config/dir/python_scripts/hello.py",
        "/some/config/dir/python_scripts/world_beer.py",
    ]
    with (
        patch(
            "menuai.components.python_script.os.path.isdir", return_value=True
        ),
        patch(
            "menuai.components.python_script.glob.iglob", return_value=scripts
        ),
    ):
        res = await async_setup_component(menuai, "python_script", {})

    assert res
    assert menuai.services.has_service("python_script", "hello")
    assert menuai.services.has_service("python_script", "world_beer")

    with (
        patch(
            "menuai.components.python_script.open",
            mock_open(read_data="fake source"),
            create=True,
        ),
        patch("menuai.components.python_script.execute") as mock_ex,
    ):
        await menuai.services.async_call(
            "python_script", "hello", {"some": "data"}, blocking=True
        )

    assert len(mock_ex.mock_calls) == 1
    test_menuai, script, source, data = mock_ex.mock_calls[0][1]

    assert test_menuai is menuai
    assert script == "hello.py"
    assert source == "fake source"
    assert data == {"some": "data"}


async def test_setup_fails_on_no_dir(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test we fail setup when no dir found."""
    with patch(
        "menuai.components.python_script.os.path.isdir", return_value=False
    ):
        res = await async_setup_component(menuai, "python_script", {})

    assert not res
    assert "Folder python_scripts not found in configuration folder" in caplog.text


async def test_execute_with_data(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test executing a script."""
    caplog.set_level(logging.WARNING)
    source = """
menuai.states.set('test.entity', data.get('name', 'not set'))
    """

    menuai.async_add_executor_job(execute, menuai, "test.py", source, {"name": "paulus"})
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert menuai.states.is_state("test.entity", "paulus")

    # No errors logged = good
    assert caplog.text == ""


async def test_execute_warns_print(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test print triggers warning."""
    caplog.set_level(logging.WARNING)
    source = """
print("This triggers warning.")
    """

    menuai.async_add_executor_job(execute, menuai, "test.py", source, {})
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert "Don't use print() inside scripts." in caplog.text


async def test_execute_logging(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test logging works."""
    caplog.set_level(logging.INFO)
    source = """
logger.info('Logging from inside script')
    """

    menuai.async_add_executor_job(execute, menuai, "test.py", source, {})
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert "Logging from inside script" in caplog.text


async def test_execute_compile_error(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test compile error logs error."""
    caplog.set_level(logging.ERROR)
    source = """
this is not valid Python
    """

    menuai.async_add_executor_job(execute, menuai, "test.py", source, {})
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert "Error loading script test.py" in caplog.text


async def test_execute_runtime_error(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test compile error logs error."""
    caplog.set_level(logging.ERROR)
    source = """
raise Exception('boom')
    """

    await menuai.async_add_executor_job(execute, menuai, "test.py", source, {})
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert "Error executing script" in caplog.text


async def test_execute_runtime_error_with_response(menuai: menuai) -> None:
    """Test compile error logs error."""
    source = """
raise Exception('boom')
    """

    task = menuai.async_add_executor_job(execute, menuai, "test.py", source, {}, True)
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert type(task.exception()) is menuaiError
    assert "Error executing script (Exception): boom" in str(task.exception())


async def test_accessing_async_methods(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test compile error logs error."""
    caplog.set_level(logging.ERROR)
    source = """
menuai.async_stop()
    """

    await menuai.async_add_executor_job(execute, menuai, "test.py", source, {})
    await menuai.async_block_till_done()

    assert "Not allowed to access async methods" in caplog.text


async def test_accessing_async_methods_with_response(menuai: menuai) -> None:
    """Test compile error logs error."""
    source = """
menuai.async_stop()
    """

    task = menuai.async_add_executor_job(execute, menuai, "test.py", source, {}, True)
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert type(task.exception()) is ServiceValidationError
    assert "Not allowed to access async methods" in str(task.exception())


async def test_using_complex_structures(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that dicts and lists work."""
    caplog.set_level(logging.INFO)
    source = """
mydict = {"a": 1, "b": 2}
mylist = [1, 2, 3, 4]
logger.info('Logging from inside script: %s %s' % (mydict["a"], mylist[2]))
    """

    await menuai.async_add_executor_job(execute, menuai, "test.py", source, {})
    await menuai.async_block_till_done()

    assert "Logging from inside script: 1 3" in caplog.text


async def test_accessing_forbidden_methods(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test compile error logs error."""
    caplog.set_level(logging.ERROR)

    for source, name in {
        "menuai.stop()": "menuai.stop",
        "dt_util.set_default_time_zone()": "module.set_default_time_zone",
        "datetime.non_existing": "module.non_existing",
        "time.tzset()": "TimeWrapper.tzset",
    }.items():
        caplog.records.clear()
        await menuai.async_add_executor_job(execute, menuai, "test.py", source, {})
        await menuai.async_block_till_done()
        assert f"Not allowed to access {name}" in caplog.text


async def test_accessing_forbidden_methods_with_response(menuai: menuai) -> None:
    """Test compile error logs error."""
    for source, name in {
        "menuai.stop()": "menuai.stop",
        "dt_util.set_default_time_zone()": "module.set_default_time_zone",
        "datetime.non_existing": "module.non_existing",
        "time.tzset()": "TimeWrapper.tzset",
    }.items():
        task = menuai.async_add_executor_job(execute, menuai, "test.py", source, {}, True)
        await menuai.async_block_till_done(wait_background_tasks=True)

        assert type(task.exception()) is ServiceValidationError
        assert f"Not allowed to access {name}" in str(task.exception())


async def test_iterating(menuai: menuai) -> None:
    """Test compile error logs error."""
    source = """
for i in [1, 2]:
    menuai.states.set('hello.{}'.format(i), 'world')
    """

    await menuai.async_add_executor_job(execute, menuai, "test.py", source, {})
    await menuai.async_block_till_done()

    assert menuai.states.is_state("hello.1", "world")
    assert menuai.states.is_state("hello.2", "world")


async def test_using_enumerate(menuai: menuai) -> None:
    """Test that enumerate is accepted and executed."""
    source = """
for index, value in enumerate(["earth", "mars"]):
    menuai.states.set('hello.{}'.format(index), value)
    """

    await menuai.async_add_executor_job(execute, menuai, "test.py", source, {})
    await menuai.async_block_till_done()

    assert menuai.states.is_state("hello.0", "earth")
    assert menuai.states.is_state("hello.1", "mars")


async def test_unpacking_sequence(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test compile error logs error."""
    caplog.set_level(logging.ERROR)
    source = """
a,b = (1,2)
ab_list = [(a,b) for a,b in [(1, 2), (3, 4)]]
menuai.states.set('hello.a', a)
menuai.states.set('hello.b', b)
menuai.states.set('hello.ab_list', '{}'.format(ab_list))
"""

    menuai.async_add_executor_job(execute, menuai, "test.py", source, {})
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert menuai.states.is_state("hello.a", "1")
    assert menuai.states.is_state("hello.b", "2")
    assert menuai.states.is_state("hello.ab_list", "[(1, 2), (3, 4)]")

    # No errors logged = good
    assert caplog.text == ""


async def test_execute_sorted(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test sorted() function."""
    caplog.set_level(logging.ERROR)
    source = """
a  = sorted([3,1,2])
assert(a == [1,2,3])
menuai.states.set('hello.a', a[0])
menuai.states.set('hello.b', a[1])
menuai.states.set('hello.c', a[2])
"""
    menuai.async_add_executor_job(execute, menuai, "test.py", source, {})
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert menuai.states.is_state("hello.a", "1")
    assert menuai.states.is_state("hello.b", "2")
    assert menuai.states.is_state("hello.c", "3")
    # No errors logged = good
    assert caplog.text == ""


async def test_exposed_modules(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test datetime and time modules exposed."""
    caplog.set_level(logging.ERROR)
    source = """
menuai.states.set('module.time', time.strftime('%Y', time.gmtime(521276400)))
menuai.states.set('module.time_strptime',
                time.strftime('%H:%M', time.strptime('12:34', '%H:%M')))
menuai.states.set('module.datetime',
                datetime.timedelta(minutes=1).total_seconds())
"""

    menuai.async_add_executor_job(execute, menuai, "test.py", source, {})
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert menuai.states.is_state("module.time", "1986")
    assert menuai.states.is_state("module.time_strptime", "12:34")
    assert menuai.states.is_state("module.datetime", "60.0")

    # No errors logged = good
    assert caplog.text == ""


async def test_execute_functions(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test functions defined in script can call one another."""
    caplog.set_level(logging.ERROR)
    source = """
def a():
    menuai.states.set('hello.a', 'one')

def b():
    a()
    menuai.states.set('hello.b', 'two')

b()
"""
    menuai.async_add_executor_job(execute, menuai, "test.py", source, {})
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert menuai.states.is_state("hello.a", "one")
    assert menuai.states.is_state("hello.b", "two")
    # No errors logged = good
    assert caplog.text == ""


async def test_reload(menuai: menuai) -> None:
    """Test we can re-discover scripts."""
    scripts = [
        "/some/config/dir/python_scripts/hello.py",
        "/some/config/dir/python_scripts/world_beer.py",
    ]
    with (
        patch(
            "menuai.components.python_script.os.path.isdir", return_value=True
        ),
        patch(
            "menuai.components.python_script.glob.iglob", return_value=scripts
        ),
    ):
        res = await async_setup_component(menuai, "python_script", {})

    assert res
    assert menuai.services.has_service("python_script", "hello")
    assert menuai.services.has_service("python_script", "world_beer")
    assert menuai.services.has_service("python_script", "reload")

    scripts = [
        "/some/config/dir/python_scripts/hello2.py",
        "/some/config/dir/python_scripts/world_beer.py",
    ]
    with (
        patch(
            "menuai.components.python_script.os.path.isdir", return_value=True
        ),
        patch(
            "menuai.components.python_script.glob.iglob", return_value=scripts
        ),
    ):
        await menuai.services.async_call("python_script", "reload", {}, blocking=True)

    assert not menuai.services.has_service("python_script", "hello")
    assert menuai.services.has_service("python_script", "hello2")
    assert menuai.services.has_service("python_script", "world_beer")
    assert menuai.services.has_service("python_script", "reload")


async def test_service_descriptions(menuai: menuai) -> None:
    """Test that service descriptions are loaded and reloaded correctly."""
    # Test 1: no user-provided services.yaml file
    scripts1 = [
        "/some/config/dir/python_scripts/hello.py",
        "/some/config/dir/python_scripts/world_beer.py",
    ]

    service_descriptions1 = (
        "hello:\n"
        "  name: ABC\n"
        "  description: Description of hello.py.\n"
        "  fields:\n"
        "    fake_param:\n"
        "      description: Parameter used by hello.py.\n"
        "      example: 'This is a test of python_script.hello'"
    )
    services_yaml1 = {
        f"{menuai.config.config_dir}/{FOLDER}/services.yaml": service_descriptions1
    }

    with (
        patch(
            "menuai.components.python_script.os.path.isdir", return_value=True
        ),
        patch(
            "menuai.components.python_script.glob.iglob", return_value=scripts1
        ),
        patch(
            "menuai.components.python_script.os.path.exists", return_value=True
        ),
        patch_yaml_files(
            services_yaml1,
        ),
    ):
        await async_setup_component(menuai, DOMAIN, {})

        descriptions = await async_get_all_descriptions(menuai)

    assert len(descriptions) == 1

    assert descriptions[DOMAIN]["hello"]["name"] == "ABC"
    assert descriptions[DOMAIN]["hello"]["description"] == "Description of hello.py."
    assert (
        descriptions[DOMAIN]["hello"]["fields"]["fake_param"]["description"]
        == "Parameter used by hello.py."
    )
    assert (
        descriptions[DOMAIN]["hello"]["fields"]["fake_param"]["example"]
        == "This is a test of python_script.hello"
    )

    # Verify default name = file name
    assert descriptions[DOMAIN]["world_beer"]["name"] == "world_beer"
    assert descriptions[DOMAIN]["world_beer"]["description"] == ""
    assert bool(descriptions[DOMAIN]["world_beer"]["fields"]) is False

    # Test 2: user-provided services.yaml file
    scripts2 = [
        "/some/config/dir/python_scripts/hello2.py",
        "/some/config/dir/python_scripts/world_beer.py",
    ]

    service_descriptions2 = (
        "hello2:\n"
        "  description: Description of hello2.py.\n"
        "  fields:\n"
        "    fake_param:\n"
        "      description: Parameter used by hello2.py.\n"
        "      example: 'This is a test of python_script.hello2'"
    )
    services_yaml2 = {
        f"{menuai.config.config_dir}/{FOLDER}/services.yaml": service_descriptions2
    }

    with (
        patch(
            "menuai.components.python_script.os.path.isdir", return_value=True
        ),
        patch(
            "menuai.components.python_script.glob.iglob", return_value=scripts2
        ),
        patch(
            "menuai.components.python_script.os.path.exists", return_value=True
        ),
        patch_yaml_files(
            services_yaml2,
        ),
    ):
        await menuai.services.async_call(DOMAIN, "reload", {}, blocking=True)
        descriptions = await async_get_all_descriptions(menuai)

    assert len(descriptions) == 1

    assert descriptions[DOMAIN]["hello2"]["description"] == "Description of hello2.py."
    assert (
        descriptions[DOMAIN]["hello2"]["fields"]["fake_param"]["description"]
        == "Parameter used by hello2.py."
    )
    assert (
        descriptions[DOMAIN]["hello2"]["fields"]["fake_param"]["example"]
        == "This is a test of python_script.hello2"
    )


async def test_sleep_warns_one(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test time.sleep warns once."""
    caplog.set_level(logging.WARNING)
    source = """
time.sleep(2)
time.sleep(5)
"""

    with patch("menuai.components.python_script.time.sleep"):
        menuai.async_add_executor_job(execute, menuai, "test.py", source, {})
        await menuai.async_block_till_done(wait_background_tasks=True)

    assert caplog.text.count("time.sleep") == 1


async def test_execute_with_output(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test executing a script with a return value."""
    caplog.set_level(logging.WARNING)

    scripts = [
        "/some/config/dir/python_scripts/hello.py",
    ]
    with (
        patch(
            "menuai.components.python_script.os.path.isdir", return_value=True
        ),
        patch(
            "menuai.components.python_script.glob.iglob", return_value=scripts
        ),
    ):
        await async_setup_component(menuai, "python_script", {})

    source = """
output = {"result": f"hello {data.get('name', 'World')}"}
    """

    with patch(
        "menuai.components.python_script.open",
        mock_open(read_data=source),
        create=True,
    ):
        response = await menuai.services.async_call(
            "python_script",
            "hello",
            {"name": "paulus"},
            blocking=True,
            return_response=True,
        )

    assert isinstance(response, dict)
    assert len(response) == 1
    assert response["result"] == "hello paulus"

    # No errors logged = good
    assert caplog.text == ""


async def test_execute_no_output(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test executing a script without a return value."""
    caplog.set_level(logging.WARNING)

    scripts = [
        "/some/config/dir/python_scripts/hello.py",
    ]
    with (
        patch(
            "menuai.components.python_script.os.path.isdir", return_value=True
        ),
        patch(
            "menuai.components.python_script.glob.iglob", return_value=scripts
        ),
    ):
        await async_setup_component(menuai, "python_script", {})

    source = """
no_output = {"result": f"hello {data.get('name', 'World')}"}
    """

    with patch(
        "menuai.components.python_script.open",
        mock_open(read_data=source),
        create=True,
    ):
        response = await menuai.services.async_call(
            "python_script",
            "hello",
            {"name": "paulus"},
            blocking=True,
            return_response=True,
        )

    assert isinstance(response, dict)
    assert len(response) == 0

    # No errors logged = good
    assert caplog.text == ""


async def test_execute_wrong_output_type(menuai: menuai) -> None:
    """Test executing a script without a return value."""
    scripts = [
        "/some/config/dir/python_scripts/hello.py",
    ]
    with (
        patch(
            "menuai.components.python_script.os.path.isdir", return_value=True
        ),
        patch(
            "menuai.components.python_script.glob.iglob", return_value=scripts
        ),
    ):
        await async_setup_component(menuai, "python_script", {})

    source = """
output = f"hello {data.get('name', 'World')}"
    """

    with (
        patch(
            "menuai.components.python_script.open",
            mock_open(read_data=source),
            create=True,
        ),
        pytest.raises(ServiceValidationError),
    ):
        await menuai.services.async_call(
            "python_script",
            "hello",
            {"name": "paulus"},
            blocking=True,
            return_response=True,
        )


async def test_augmented_assignment_operations(menuai: menuai) -> None:
    """Test that augmented assignment operations work."""
    source = """
a = 10
a += 20
a *= 5
a -= 8
b = "foo"
b += "bar"
b *= 2
c = []
c += [1, 2, 3]
c *= 2
menuai.states.set('hello.a', a)
menuai.states.set('hello.b', b)
menuai.states.set('hello.c', c)
    """

    menuai.async_add_executor_job(execute, menuai, "aug_assign.py", source, {})
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert menuai.states.get("hello.a").state == str(((10 + 20) * 5) - 8)
    assert menuai.states.get("hello.b").state == ("foo" + "bar") * 2
    assert menuai.states.get("hello.c").state == str([1, 2, 3] * 2)


@pytest.mark.parametrize(
    ("case", "error"),
    [
        pytest.param(
            "d = datetime.date(2024, 1, 1); d += 5",
            "The '+=' operation is not allowed",
            id="datetime.date",
        ),
    ],
)
async def test_prohibited_augmented_assignment_operations(
    menuai: menuai, case: str, error: str, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that prohibited augmented assignment operations raise an error."""
    menuai.async_add_executor_job(execute, menuai, "aug_assign_prohibited.py", case, {})
    await menuai.async_block_till_done(wait_background_tasks=True)
    assert error in caplog.text


async def test_import_allow_strptime(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test calling datetime.datetime.strptime works."""
    source = """
test_date = datetime.datetime.strptime('2024-04-01', '%Y-%m-%d')
logger.info(f'Date {test_date}')
    """
    menuai.async_add_executor_job(execute, menuai, "test.py", source, {})
    await menuai.async_block_till_done(wait_background_tasks=True)
    assert "Error executing script: Not allowed to import _strptime" not in caplog.text
    assert "Date 2024-04-01 00:00:00" in caplog.text


async def test_no_other_imports_allowed(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test imports are not allowed."""
    source = "import sys"
    menuai.async_add_executor_job(execute, menuai, "test.py", source, {})
    await menuai.async_block_till_done(wait_background_tasks=True)
    assert "ImportError: Not allowed to import sys" in caplog.text
