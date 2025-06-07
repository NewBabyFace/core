"""Test requirements module."""

import asyncio
import logging
import os
from unittest.mock import call, patch

import pytest

from menuai import loader, setup
from menuai.core import menuai
from menuai.loader import async_get_integration
from menuai.requirements import (
    CONSTRAINT_FILE,
    RequirementsNotFound,
    _async_get_manager,
    async_clear_install_history,
    async_get_integration_with_requirements,
    async_process_requirements,
)

from .common import MockModule, mock_integration


def env_without_wheel_links():
    """Return env without wheel links."""
    env = dict(os.environ)
    env.pop("WHEEL_LINKS", None)
    return env


async def test_requirement_installed_in_venv(menuai: menuai) -> None:
    """Test requirement installed in virtual environment."""
    with (
        patch("os.path.dirname", return_value="ha_package_path"),
        patch("menuai.util.package.is_virtual_env", return_value=True),
        patch("menuai.util.package.is_docker_env", return_value=False),
        patch(
            "menuai.util.package.install_package", return_value=True
        ) as mock_install,
        patch.dict(os.environ, env_without_wheel_links(), clear=True),
    ):
        menuai.config.skip_pip = False
        mock_integration(menuai, MockModule("comp", requirements=["package==0.0.1"]))
        assert await setup.async_setup_component(menuai, "comp", {})
        assert "comp" in menuai.config.components
        assert mock_install.call_args == call(
            "package==0.0.1",
            constraints=os.path.join("ha_package_path", CONSTRAINT_FILE),
            timeout=60,
        )


async def test_requirement_installed_in_deps(menuai: menuai) -> None:
    """Test requirement installed in deps directory."""
    with (
        patch("os.path.dirname", return_value="ha_package_path"),
        patch("menuai.util.package.is_virtual_env", return_value=False),
        patch("menuai.util.package.is_docker_env", return_value=False),
        patch(
            "menuai.util.package.install_package", return_value=True
        ) as mock_install,
        patch.dict(os.environ, env_without_wheel_links(), clear=True),
    ):
        menuai.config.skip_pip = False
        mock_integration(menuai, MockModule("comp", requirements=["package==0.0.1"]))
        assert await setup.async_setup_component(menuai, "comp", {})
        assert "comp" in menuai.config.components
        assert mock_install.call_args == call(
            "package==0.0.1",
            target=menuai.config.path("deps"),
            constraints=os.path.join("ha_package_path", CONSTRAINT_FILE),
            timeout=60,
        )


async def test_install_existing_package(menuai: menuai) -> None:
    """Test an install attempt on an existing package."""
    with patch(
        "menuai.util.package.install_package", return_value=True
    ) as mock_inst:
        await async_process_requirements(menuai, "test_component", ["hello==1.0.0"])

    assert len(mock_inst.mock_calls) == 1

    with (
        patch("menuai.util.package.is_installed", return_value=True),
        patch("menuai.util.package.install_package") as mock_inst,
    ):
        await async_process_requirements(menuai, "test_component", ["hello==1.0.0"])

    assert len(mock_inst.mock_calls) == 0


async def test_install_missing_package(menuai: menuai) -> None:
    """Test an install attempt on an existing package."""
    with (
        patch(
            "menuai.util.package.install_package", return_value=False
        ) as mock_inst,
        pytest.raises(RequirementsNotFound),
    ):
        await async_process_requirements(menuai, "test_component", ["hello==1.0.0"])

    assert len(mock_inst.mock_calls) == 3


async def test_install_skipped_package(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test an install attempt on a dependency that should be skipped."""
    with patch(
        "menuai.util.package.install_package", return_value=True
    ) as mock_inst:
        menuai.config.skip_pip_packages = ["hello"]
        with caplog.at_level(logging.WARNING):
            await async_process_requirements(
                menuai, "test_component", ["hello==1.0.0", "not_skipped==1.2.3"]
            )

    assert "Skipping requirement hello==1.0.0" in caplog.text

    assert len(mock_inst.mock_calls) == 1
    assert mock_inst.mock_calls[0].args[0] == "not_skipped==1.2.3"


async def test_get_integration_with_requirements(menuai: menuai) -> None:
    """Check getting an integration with loaded requirements."""
    menuai.config.skip_pip = False
    mock_integration(
        menuai, MockModule("test_component_dep", requirements=["test-comp-dep==1.0.0"])
    )
    mock_integration(
        menuai,
        MockModule(
            "test_component_after_dep", requirements=["test-comp-after-dep==1.0.0"]
        ),
    )
    mock_integration(
        menuai,
        MockModule(
            "test_component",
            requirements=["test-comp==1.0.0"],
            dependencies=["test_component_dep"],
            partial_manifest={"after_dependencies": ["test_component_after_dep"]},
        ),
    )

    with (
        patch(
            "menuai.util.package.is_installed", return_value=False
        ) as mock_is_installed,
        patch(
            "menuai.util.package.install_package", return_value=True
        ) as mock_inst,
    ):
        integration = await async_get_integration_with_requirements(
            menuai, "test_component"
        )
        assert integration
        assert integration.domain == "test_component"

    assert len(mock_is_installed.mock_calls) == 3
    assert sorted(mock_call[1][0] for mock_call in mock_is_installed.mock_calls) == [
        "test-comp-after-dep==1.0.0",
        "test-comp-dep==1.0.0",
        "test-comp==1.0.0",
    ]

    assert len(mock_inst.mock_calls) == 3
    assert sorted(mock_call[1][0] for mock_call in mock_inst.mock_calls) == [
        "test-comp-after-dep==1.0.0",
        "test-comp-dep==1.0.0",
        "test-comp==1.0.0",
    ]


async def test_get_integration_with_requirements_cache(menuai: menuai) -> None:
    """Check getting an integration with loaded requirements considers cache.

    We want to make sure that we do not check requirements for dependencies
    that we have already checked.
    """
    menuai.config.skip_pip = False
    mock_integration(
        menuai, MockModule("test_component_dep", requirements=["test-comp-dep==1.0.0"])
    )
    mock_integration(
        menuai,
        MockModule(
            "test_component_after_dep", requirements=["test-comp-after-dep==1.0.0"]
        ),
    )
    mock_integration(
        menuai,
        MockModule(
            "test_component",
            requirements=["test-comp==1.0.0"],
            dependencies=["test_component_dep"],
            partial_manifest={"after_dependencies": ["test_component_after_dep"]},
        ),
    )
    mock_integration(
        menuai,
        MockModule(
            "test_component2",
            requirements=["test-comp2==1.0.0"],
            dependencies=["test_component_dep"],
            partial_manifest={"after_dependencies": ["test_component_after_dep"]},
        ),
    )

    with (
        patch(
            "menuai.util.package.is_installed", return_value=False
        ) as mock_is_installed,
        patch(
            "menuai.util.package.install_package", return_value=True
        ) as mock_inst,
        patch(
            "menuai.requirements.async_get_integration",
            wraps=async_get_integration,
        ) as mock_async_get_integration,
    ):
        integration = await async_get_integration_with_requirements(
            menuai, "test_component"
        )
        assert integration
        assert integration.domain == "test_component"

        assert len(mock_is_installed.mock_calls) == 3
        assert sorted(
            mock_call[1][0] for mock_call in mock_is_installed.mock_calls
        ) == [
            "test-comp-after-dep==1.0.0",
            "test-comp-dep==1.0.0",
            "test-comp==1.0.0",
        ]

        assert len(mock_inst.mock_calls) == 3
        assert sorted(mock_call[1][0] for mock_call in mock_inst.mock_calls) == [
            "test-comp-after-dep==1.0.0",
            "test-comp-dep==1.0.0",
            "test-comp==1.0.0",
        ]

        # The dependent integrations should be fetched since
        assert len(mock_async_get_integration.mock_calls) == 3
        assert sorted(
            mock_call[1][1] for mock_call in mock_async_get_integration.mock_calls
        ) == ["test_component", "test_component_after_dep", "test_component_dep"]

        # test_component2 has the same deps as test_component and we should
        # not check the requirements for the deps again

        mock_is_installed.reset_mock()
        mock_inst.reset_mock()
        mock_async_get_integration.reset_mock()

        integration = await async_get_integration_with_requirements(
            menuai, "test_component2"
        )

    assert integration
    assert integration.domain == "test_component2"

    assert len(mock_is_installed.mock_calls) == 1
    assert sorted(mock_call[1][0] for mock_call in mock_is_installed.mock_calls) == [
        "test-comp2==1.0.0",
    ]

    assert len(mock_inst.mock_calls) == 1
    assert sorted(mock_call[1][0] for mock_call in mock_inst.mock_calls) == [
        "test-comp2==1.0.0",
    ]

    # The dependent integrations should not be fetched again
    assert len(mock_async_get_integration.mock_calls) == 1
    assert sorted(
        mock_call[1][1] for mock_call in mock_async_get_integration.mock_calls
    ) == [
        "test_component2",
    ]


async def test_get_integration_with_requirements_concurrency(
    menuai: menuai,
) -> None:
    """Test that we don't install the same requirement concurrently."""
    menuai.config.skip_pip = False
    mock_integration(
        menuai, MockModule("test_component_dep", requirements=["test-comp-dep==1.0.0"])
    )

    process_integration_calls = 0

    async def _async_process_integration_slowed(*args, **kwargs):
        nonlocal process_integration_calls
        process_integration_calls += 1
        await asyncio.sleep(0)

    manager = _async_get_manager(menuai)
    with patch.object(
        manager, "_async_process_integration", _async_process_integration_slowed
    ):
        tasks = [
            async_get_integration_with_requirements(menuai, "test_component_dep")
            for _ in range(10)
        ]
        results = await asyncio.gather(*tasks)
        assert all(result.domain == "test_component_dep" for result in results)

    assert process_integration_calls == 1


async def test_get_integration_with_requirements_pip_install_fails_two_passes(
    menuai: menuai,
) -> None:
    """Check getting an integration with loaded requirements and the pip install fails two passes."""
    menuai.config.skip_pip = False
    mock_integration(
        menuai, MockModule("test_component_dep", requirements=["test-comp-dep==1.0.0"])
    )
    mock_integration(
        menuai,
        MockModule(
            "test_component_after_dep", requirements=["test-comp-after-dep==1.0.0"]
        ),
    )
    mock_integration(
        menuai,
        MockModule(
            "test_component",
            requirements=["test-comp==1.0.0"],
            dependencies=["test_component_dep"],
            partial_manifest={"after_dependencies": ["test_component_after_dep"]},
        ),
    )

    def _mock_install_package(package, **kwargs):
        if package == "test-comp==1.0.0":
            return True
        return False

    # 1st pass
    with (
        pytest.raises(RequirementsNotFound),
        patch(
            "menuai.util.package.is_installed", return_value=False
        ) as mock_is_installed,
        patch(
            "menuai.util.package.install_package",
            side_effect=_mock_install_package,
        ) as mock_inst,
    ):
        integration = await async_get_integration_with_requirements(
            menuai, "test_component"
        )

    assert len(mock_is_installed.mock_calls) == 3
    assert sorted(mock_call[1][0] for mock_call in mock_is_installed.mock_calls) == [
        "test-comp-after-dep==1.0.0",
        "test-comp-dep==1.0.0",
        "test-comp==1.0.0",
    ]

    assert len(mock_inst.mock_calls) == 7
    assert sorted(mock_call[1][0] for mock_call in mock_inst.mock_calls) == [
        "test-comp-after-dep==1.0.0",
        "test-comp-after-dep==1.0.0",
        "test-comp-after-dep==1.0.0",
        "test-comp-dep==1.0.0",
        "test-comp-dep==1.0.0",
        "test-comp-dep==1.0.0",
        "test-comp==1.0.0",
    ]

    # 2nd pass
    with (
        pytest.raises(RequirementsNotFound),
        patch(
            "menuai.util.package.is_installed", return_value=False
        ) as mock_is_installed,
        patch(
            "menuai.util.package.install_package",
            side_effect=_mock_install_package,
        ) as mock_inst,
    ):
        integration = await async_get_integration_with_requirements(
            menuai, "test_component"
        )

    assert len(mock_is_installed.mock_calls) == 0
    # On another attempt we remember failures and don't try again
    assert len(mock_inst.mock_calls) == 0

    # Now clear the history and so we try again
    async_clear_install_history(menuai)

    with (
        pytest.raises(RequirementsNotFound),
        patch(
            "menuai.util.package.is_installed", return_value=False
        ) as mock_is_installed,
        patch(
            "menuai.util.package.install_package",
            side_effect=_mock_install_package,
        ) as mock_inst,
    ):
        integration = await async_get_integration_with_requirements(
            menuai, "test_component"
        )

    assert len(mock_is_installed.mock_calls) == 2
    assert sorted(mock_call[1][0] for mock_call in mock_is_installed.mock_calls) == [
        "test-comp-after-dep==1.0.0",
        "test-comp-dep==1.0.0",
    ]

    assert len(mock_inst.mock_calls) == 6
    assert sorted(mock_call[1][0] for mock_call in mock_inst.mock_calls) == [
        "test-comp-after-dep==1.0.0",
        "test-comp-after-dep==1.0.0",
        "test-comp-after-dep==1.0.0",
        "test-comp-dep==1.0.0",
        "test-comp-dep==1.0.0",
        "test-comp-dep==1.0.0",
    ]

    # Now clear the history and mock success
    async_clear_install_history(menuai)

    with (
        patch(
            "menuai.util.package.is_installed", return_value=False
        ) as mock_is_installed,
        patch(
            "menuai.util.package.install_package", return_value=True
        ) as mock_inst,
    ):
        integration = await async_get_integration_with_requirements(
            menuai, "test_component"
        )
        assert integration
        assert integration.domain == "test_component"

    assert len(mock_is_installed.mock_calls) == 2
    assert sorted(mock_call[1][0] for mock_call in mock_is_installed.mock_calls) == [
        "test-comp-after-dep==1.0.0",
        "test-comp-dep==1.0.0",
    ]

    assert len(mock_inst.mock_calls) == 2
    assert sorted(mock_call[1][0] for mock_call in mock_inst.mock_calls) == [
        "test-comp-after-dep==1.0.0",
        "test-comp-dep==1.0.0",
    ]


async def test_get_integration_with_missing_dependencies(menuai: menuai) -> None:
    """Check getting an integration with missing dependencies."""
    menuai.config.skip_pip = False
    mock_integration(
        menuai,
        MockModule("test_component_after_dep"),
    )
    mock_integration(
        menuai,
        MockModule(
            "test_component",
            dependencies=["test_component_dep"],
            partial_manifest={"after_dependencies": ["test_component_after_dep"]},
        ),
    )
    mock_integration(
        menuai,
        MockModule(
            "test_custom_component",
            dependencies=["test_component_dep"],
            partial_manifest={"after_dependencies": ["test_component_after_dep"]},
        ),
        built_in=False,
    )
    with pytest.raises(loader.IntegrationNotFound):
        await async_get_integration_with_requirements(menuai, "test_component")
    with pytest.raises(loader.IntegrationNotFound):
        await async_get_integration_with_requirements(menuai, "test_custom_component")


async def test_get_built_in_integration_with_missing_after_dependencies(
    menuai: menuai,
) -> None:
    """Check getting a built_in integration with missing after_dependencies results in exception."""
    menuai.config.skip_pip = False
    mock_integration(
        menuai,
        MockModule(
            "test_component",
            partial_manifest={"after_dependencies": ["test_component_after_dep"]},
        ),
        built_in=True,
    )
    with pytest.raises(loader.IntegrationNotFound):
        await async_get_integration_with_requirements(menuai, "test_component")


async def test_get_custom_integration_with_missing_after_dependencies(
    menuai: menuai,
) -> None:
    """Check getting a custom integration with missing after_dependencies."""
    menuai.config.skip_pip = False
    mock_integration(
        menuai,
        MockModule(
            "test_custom_component",
            partial_manifest={"after_dependencies": ["test_component_after_dep"]},
        ),
        built_in=False,
    )
    integration = await async_get_integration_with_requirements(
        menuai, "test_custom_component"
    )
    assert integration
    assert integration.domain == "test_custom_component"


async def test_install_with_wheels_index(menuai: menuai) -> None:
    """Test an install attempt with wheels index URL."""
    menuai.config.skip_pip = False
    mock_integration(menuai, MockModule("comp", requirements=["hello==1.0.0"]))

    with (
        patch("menuai.util.package.is_installed", return_value=False),
        patch("menuai.util.package.is_docker_env", return_value=True),
        patch("menuai.util.package.install_package") as mock_inst,
        patch.dict(os.environ, {"WHEELS_LINKS": "https://wheels.menuai.io/test"}),
        patch(
            "os.path.dirname",
        ) as mock_dir,
    ):
        mock_dir.return_value = "ha_package_path"
        assert await setup.async_setup_component(menuai, "comp", {})
        assert "comp" in menuai.config.components

        assert mock_inst.call_args == call(
            "hello==1.0.0",
            constraints=os.path.join("ha_package_path", CONSTRAINT_FILE),
            timeout=60,
        )


async def test_install_on_docker(menuai: menuai) -> None:
    """Test an install attempt on an docker system env."""
    menuai.config.skip_pip = False
    mock_integration(menuai, MockModule("comp", requirements=["hello==1.0.0"]))

    with (
        patch("menuai.util.package.is_installed", return_value=False),
        patch("menuai.util.package.is_docker_env", return_value=True),
        patch("menuai.util.package.install_package") as mock_inst,
        patch("os.path.dirname") as mock_dir,
        patch.dict(os.environ, env_without_wheel_links(), clear=True),
    ):
        mock_dir.return_value = "ha_package_path"
        assert await setup.async_setup_component(menuai, "comp", {})
        assert "comp" in menuai.config.components

        assert mock_inst.call_args == call(
            "hello==1.0.0",
            constraints=os.path.join("ha_package_path", CONSTRAINT_FILE),
            timeout=60,
        )


async def test_discovery_requirements_mqtt(menuai: menuai) -> None:
    """Test that we load discovery requirements."""
    menuai.config.skip_pip = False
    mqtt = await loader.async_get_integration(menuai, "mqtt")

    mock_integration(
        menuai, MockModule("mqtt_comp", partial_manifest={"mqtt": ["foo/discovery"]})
    )
    with patch(
        "menuai.requirements.RequirementsManager.async_process_requirements",
    ) as mock_process:
        await async_get_integration_with_requirements(menuai, "mqtt_comp")

    assert len(mock_process.mock_calls) == 2
    # one for mqtt and one for menuaiio
    assert mock_process.mock_calls[0][1][1] == mqtt.requirements


async def test_discovery_requirements_ssdp(menuai: menuai) -> None:
    """Test that we load discovery requirements."""
    menuai.config.skip_pip = False
    ssdp = await loader.async_get_integration(menuai, "ssdp")

    mock_integration(
        menuai, MockModule("ssdp_comp", partial_manifest={"ssdp": [{"st": "roku:ecp"}]})
    )
    with patch(
        "menuai.requirements.RequirementsManager.async_process_requirements",
    ) as mock_process:
        await async_get_integration_with_requirements(menuai, "ssdp_comp")

    assert len(mock_process.mock_calls) == 2
    assert mock_process.mock_calls[0][1][1] == ssdp.requirements
    assert {
        mock_process.mock_calls[0][1][0],
        mock_process.mock_calls[1][1][0],
    } == {"network", "ssdp"}


@pytest.mark.parametrize(
    "partial_manifest",
    [{"zeroconf": ["_googlecast._tcp.local."]}, {"homekit": {"models": ["LIFX"]}}],
)
async def test_discovery_requirements_zeroconf(
    menuai: menuai, partial_manifest
) -> None:
    """Test that we load discovery requirements."""
    menuai.config.skip_pip = False
    zeroconf = await loader.async_get_integration(menuai, "zeroconf")

    mock_integration(
        menuai,
        MockModule("comp", partial_manifest=partial_manifest),
    )

    with patch(
        "menuai.requirements.RequirementsManager.async_process_requirements",
    ) as mock_process:
        await async_get_integration_with_requirements(menuai, "comp")

    assert len(mock_process.mock_calls) == 2
    assert mock_process.mock_calls[0][1][1] == zeroconf.requirements


async def test_discovery_requirements_dhcp(menuai: menuai) -> None:
    """Test that we load dhcp discovery requirements."""
    menuai.config.skip_pip = False
    dhcp = await loader.async_get_integration(menuai, "dhcp")

    mock_integration(
        menuai,
        MockModule(
            "comp",
            partial_manifest={
                "dhcp": [{"hostname": "somfy_*", "macaddress": "B8B7F1*"}]
            },
        ),
    )
    with patch(
        "menuai.requirements.RequirementsManager.async_process_requirements",
    ) as mock_process:
        await async_get_integration_with_requirements(menuai, "comp")

    assert len(mock_process.mock_calls) == 2  # dhcp does not depend on http
    assert mock_process.mock_calls[0][1][1] == dhcp.requirements
