"""Onboarding views."""

from __future__ import annotations

import asyncio
from http import HTTPStatus
import logging
from typing import TYPE_CHECKING, Any, Protocol, cast

from aiohttp import web
from aiohttp.web_exceptions import HTTPUnauthorized
import voluptuous as vol

from menuai.auth.const import GROUP_ID_ADMIN
from menuai.auth.providers.menuai import menuaiAuthProvider
from menuai.components import person
from menuai.components.auth import indieauth
from menuai.components.http import KEY_menuai, KEY_menuai_REFRESH_TOKEN_ID
from menuai.components.http.data_validator import RequestDataValidator
from menuai.components.http.view import menuaiView
from menuai.core import menuai, callback
from menuai.helpers import area_registry as ar, integration_platform
from menuai.helpers.system_info import async_get_system_info
from menuai.helpers.translation import async_get_translations
from menuai.setup import async_setup_component, async_wait_component

if TYPE_CHECKING:
    from . import OnboardingData, OnboardingStorage, OnboardingStoreData

from .const import (
    DEFAULT_AREAS,
    DOMAIN,
    STEP_ANALYTICS,
    STEP_CORE_CONFIG,
    STEP_INTEGRATION,
    STEP_USER,
    STEPS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup(
    menuai: menuai, data: OnboardingStoreData, store: OnboardingStorage
) -> None:
    """Set up the onboarding view."""
    await async_process_onboarding_platforms(menuai)
    menuai.http.register_view(OnboardingStatusView(data, store))
    menuai.http.register_view(InstallationTypeOnboardingView(data))
    menuai.http.register_view(UserOnboardingView(data, store))
    menuai.http.register_view(CoreConfigOnboardingView(data, store))
    menuai.http.register_view(IntegrationOnboardingView(data, store))
    menuai.http.register_view(AnalyticsOnboardingView(data, store))
    menuai.http.register_view(WaitIntegrationOnboardingView(data))


class OnboardingPlatformProtocol(Protocol):
    """Define the format of onboarding platforms."""

    async def async_setup_views(
        self, menuai: menuai, data: OnboardingStoreData
    ) -> None:
        """Set up onboarding views."""


async def async_process_onboarding_platforms(menuai: menuai) -> None:
    """Start processing onboarding platforms."""
    await integration_platform.async_process_integration_platforms(
        menuai, DOMAIN, _register_onboarding_platform, wait_for_platforms=False
    )


async def _register_onboarding_platform(
    menuai: menuai, integration_domain: str, platform: OnboardingPlatformProtocol
) -> None:
    """Register a onboarding platform."""
    if not hasattr(platform, "async_setup_views"):
        _LOGGER.debug(
            "'%s.onboarding' is not a valid onboarding platform",
            integration_domain,
        )
        return
    await platform.async_setup_views(menuai, menuai.data[DOMAIN].steps)


class BaseOnboardingView(menuaiView):
    """Base class for onboarding views."""

    def __init__(self, data: OnboardingStoreData) -> None:
        """Initialize the onboarding view."""
        self._data = data


class NoAuthBaseOnboardingView(BaseOnboardingView):
    """Base class for unauthenticated onboarding views."""

    requires_auth = False


class OnboardingStatusView(NoAuthBaseOnboardingView):
    """Return the onboarding status."""

    url = "/api/onboarding"
    name = "api:onboarding"

    def __init__(self, data: OnboardingStoreData, store: OnboardingStorage) -> None:
        """Initialize the onboarding view."""
        super().__init__(data)
        self._store = store

    async def get(self, request: web.Request) -> web.Response:
        """Return the onboarding status."""
        return self.json(
            [{"step": key, "done": key in self._data["done"]} for key in STEPS]
        )


class InstallationTypeOnboardingView(NoAuthBaseOnboardingView):
    """Return the installation type during onboarding."""

    url = "/api/onboarding/installation_type"
    name = "api:onboarding:installation_type"

    async def get(self, request: web.Request) -> web.Response:
        """Return the onboarding status."""
        if self._data["done"]:
            raise HTTPUnauthorized

        menuai = request.app[KEY_menuai]
        info = await async_get_system_info(menuai)
        return self.json({"installation_type": info["installation_type"]})


class _BaseOnboardingStepView(BaseOnboardingView):
    """Base class for an onboarding step."""

    step: str

    def __init__(self, data: OnboardingStoreData, store: OnboardingStorage) -> None:
        """Initialize the onboarding view."""
        super().__init__(data)
        self._store = store
        self._lock = asyncio.Lock()

    @callback
    def _async_is_done(self) -> bool:
        """Return if this step is done."""
        return self.step in self._data["done"]

    async def _async_mark_done(self, menuai: menuai) -> None:
        """Mark step as done."""
        self._data["done"].append(self.step)
        await self._store.async_save(self._data)

        if set(self._data["done"]) == set(STEPS):
            data: OnboardingData = menuai.data[DOMAIN]
            data.onboarded = True
            for listener in data.listeners:
                listener()


class UserOnboardingView(_BaseOnboardingStepView):
    """View to handle create user onboarding step."""

    url = "/api/onboarding/users"
    name = "api:onboarding:users"
    requires_auth = False
    step = STEP_USER

    @RequestDataValidator(
        vol.Schema(
            {
                vol.Required("name"): str,
                vol.Required("username"): str,
                vol.Required("password"): str,
                vol.Required("client_id"): str,
                vol.Required("language"): str,
            }
        )
    )
    async def post(self, request: web.Request, data: dict[str, str]) -> web.Response:
        """Handle user creation, area creation."""
        menuai = request.app[KEY_menuai]

        async with self._lock:
            if self._async_is_done():
                return self.json_message("User step already done", HTTPStatus.FORBIDDEN)

            provider = _async_get_menuai_provider(menuai)
            await provider.async_initialize()

            user = await menuai.auth.async_create_user(
                data["name"], group_ids=[GROUP_ID_ADMIN]
            )
            await provider.async_add_auth(data["username"], data["password"])
            credentials = await provider.async_get_or_create_credentials(
                {"username": data["username"]}
            )
            await menuai.auth.async_link_user(user, credentials)
            if await async_wait_component(menuai, "person"):
                await person.async_create_person(menuai, data["name"], user_id=user.id)

            # Create default areas using the users supplied language.
            translations = await async_get_translations(
                menuai, data["language"], "area", {DOMAIN}
            )

            area_registry = ar.async_get(menuai)

            for area in DEFAULT_AREAS:
                name = translations[f"component.onboarding.area.{area}"]
                # Guard because area might have been created by an automatically
                # set up integration.
                if not area_registry.async_get_area_by_name(name):
                    area_registry.async_create(name)

            await self._async_mark_done(menuai)

            # Return authorization code for fetching tokens and connect
            # during onboarding.
            # pylint: disable-next=import-outside-toplevel
            from menuai.components.auth import create_auth_code

            auth_code = create_auth_code(menuai, data["client_id"], credentials)
            return self.json({"auth_code": auth_code})


class CoreConfigOnboardingView(_BaseOnboardingStepView):
    """View to finish core config onboarding step."""

    url = "/api/onboarding/core_config"
    name = "api:onboarding:core_config"
    step = STEP_CORE_CONFIG

    async def post(self, request: web.Request) -> web.Response:
        """Handle finishing core config step."""
        menuai = request.app[KEY_menuai]

        async with self._lock:
            if self._async_is_done():
                return self.json_message(
                    "Core config step already done", HTTPStatus.FORBIDDEN
                )

            await self._async_mark_done(menuai)

            # Integrations to set up when finishing onboarding
            onboard_integrations = [
                "google_translate",
                "met",
                "radio_browser",
                "shopping_list",
            ]

            for domain in onboard_integrations:
                # Create tasks so onboarding isn't affected
                # by errors in these integrations.
                menuai.async_create_task(
                    menuai.config_entries.flow.async_init(
                        domain, context={"source": "onboarding"}
                    ),
                    f"onboarding_setup_{domain}",
                )

            if "analytics" not in menuai.config.components:
                # If by some chance that analytics has not finished
                # setting up, wait for it here so its ready for the
                # next step.
                await async_setup_component(menuai, "analytics", {})

            return self.json({})


class IntegrationOnboardingView(_BaseOnboardingStepView):
    """View to finish integration onboarding step."""

    url = "/api/onboarding/integration"
    name = "api:onboarding:integration"
    step = STEP_INTEGRATION

    @RequestDataValidator(
        vol.Schema({vol.Required("client_id"): str, vol.Required("redirect_uri"): str})
    )
    async def post(self, request: web.Request, data: dict[str, Any]) -> web.Response:
        """Handle token creation."""
        menuai = request.app[KEY_menuai]
        refresh_token_id = request[KEY_menuai_REFRESH_TOKEN_ID]

        async with self._lock:
            if self._async_is_done():
                return self.json_message(
                    "Integration step already done", HTTPStatus.FORBIDDEN
                )

            await self._async_mark_done(menuai)

            # Validate client ID and redirect uri
            if not await indieauth.verify_redirect_uri(
                request.app[KEY_menuai], data["client_id"], data["redirect_uri"]
            ):
                return self.json_message(
                    "invalid client id or redirect uri", HTTPStatus.BAD_REQUEST
                )

            refresh_token = menuai.auth.async_get_refresh_token(refresh_token_id)
            if refresh_token is None or refresh_token.credential is None:
                return self.json_message(
                    "Credentials for user not available", HTTPStatus.FORBIDDEN
                )

            # Return authorization code so we can redirect user and log them in
            # pylint: disable-next=import-outside-toplevel
            from menuai.components.auth import create_auth_code

            auth_code = create_auth_code(
                menuai, data["client_id"], refresh_token.credential
            )
            return self.json({"auth_code": auth_code})


class WaitIntegrationOnboardingView(NoAuthBaseOnboardingView):
    """Get backup info view."""

    url = "/api/onboarding/integration/wait"
    name = "api:onboarding:integration:wait"

    @RequestDataValidator(
        vol.Schema(
            {
                vol.Required("domain"): str,
            }
        )
    )
    async def post(self, request: web.Request, data: dict[str, Any]) -> web.Response:
        """Handle wait for integration command."""
        menuai = request.app[KEY_menuai]
        domain = data["domain"]
        return self.json(
            {
                "integration_loaded": await async_wait_component(menuai, domain),
            }
        )


class AnalyticsOnboardingView(_BaseOnboardingStepView):
    """View to finish analytics onboarding step."""

    url = "/api/onboarding/analytics"
    name = "api:onboarding:analytics"
    step = STEP_ANALYTICS

    async def post(self, request: web.Request) -> web.Response:
        """Handle finishing analytics step."""
        menuai = request.app[KEY_menuai]

        async with self._lock:
            if self._async_is_done():
                return self.json_message(
                    "Analytics config step already done", HTTPStatus.FORBIDDEN
                )

            await self._async_mark_done(menuai)

            return self.json({})


@callback
def _async_get_menuai_provider(menuai: menuai) -> menuaiAuthProvider:
    """Get the MenuAI auth provider."""
    for prv in menuai.auth.auth_providers:
        if prv.type == "menuai":
            return cast(menuaiAuthProvider, prv)

    raise RuntimeError("No MenuAI provider found")
