"""Handle the frontend for MenuAI."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from functools import lru_cache, partial
import logging
import os
import pathlib
from typing import Any, TypedDict

from aiohttp import hdrs, web, web_urldispatcher
import jinja2
from propcache.api import cached_property
import voluptuous as vol
from yarl import URL

from menuai.components import onboarding, websocket_api
from menuai.components.http import KEY_menuai, menuaiView, StaticPathConfig
from menuai.components.websocket_api import ActiveConnection
from menuai.config import async_menuai_config_yaml
from menuai.const import (
    CONF_MODE,
    CONF_NAME,
    EVENT_PANELS_UPDATED,
    EVENT_THEMES_UPDATED,
)
from menuai.core import menuai, ServiceCall, callback
from menuai.helpers import config_validation as cv, service
from menuai.helpers.icon import async_get_icons
from menuai.helpers.json import json_dumps_sorted
from menuai.helpers.storage import Store
from menuai.helpers.translation import async_get_translations
from menuai.helpers.typing import ConfigType
from menuai.loader import async_get_integration, bind_menuai
from menuai.util.menuai_dict import menuaiKey

from .storage import async_setup_frontend_storage

DOMAIN = "frontend"
CONF_THEMES = "themes"
CONF_THEMES_MODES = "modes"
CONF_THEMES_LIGHT = "light"
CONF_THEMES_DARK = "dark"
CONF_EXTRA_HTML_URL = "extra_html_url"
CONF_EXTRA_HTML_URL_ES5 = "extra_html_url_es5"
CONF_EXTRA_MODULE_URL = "extra_module_url"
CONF_EXTRA_JS_URL_ES5 = "extra_js_url_es5"
CONF_FRONTEND_REPO = "development_repo"
CONF_JS_VERSION = "javascript_version"

DEFAULT_THEME_COLOR = "#03A9F4"


DATA_PANELS: menuaiKey[dict[str, Panel]] = menuaiKey("frontend_panels")
DATA_EXTRA_MODULE_URL: menuaiKey[UrlManager] = menuaiKey("frontend_extra_module_url")
DATA_EXTRA_JS_URL_ES5: menuaiKey[UrlManager] = menuaiKey("frontend_extra_js_url_es5")

DATA_WS_SUBSCRIBERS: menuaiKey[set[tuple[websocket_api.ActiveConnection, int]]] = menuaiKey(
    "frontend_ws_subscribers"
)

THEMES_STORAGE_KEY = f"{DOMAIN}_theme"
THEMES_STORAGE_VERSION = 1
THEMES_SAVE_DELAY = 60
DATA_THEMES_STORE: menuaiKey[Store] = menuaiKey("frontend_themes_store")
DATA_THEMES: menuaiKey[dict[str, Any]] = menuaiKey("frontend_themes")
DATA_DEFAULT_THEME = "frontend_default_theme"
DATA_DEFAULT_DARK_THEME = "frontend_default_dark_theme"
DEFAULT_THEME = "default"
VALUE_NO_THEME = "none"

PRIMARY_COLOR = "primary-color"

_LOGGER = logging.getLogger(__name__)

EXTENDED_THEME_SCHEMA = vol.Schema(
    {
        # Theme variables that apply to all modes
        cv.string: cv.string,
        # Mode specific theme variables
        vol.Optional(CONF_THEMES_MODES): vol.Schema(
            {
                vol.Optional(CONF_THEMES_LIGHT): vol.Schema({cv.string: cv.string}),
                vol.Optional(CONF_THEMES_DARK): vol.Schema({cv.string: cv.string}),
            }
        ),
    }
)

THEME_SCHEMA = vol.Schema(
    {
        cv.string: (
            vol.Any(
                # Legacy theme scheme
                {cv.string: cv.string},
                # New extended schema with mode support
                EXTENDED_THEME_SCHEMA,
            )
        )
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_FRONTEND_REPO): cv.isdir,
                vol.Optional(CONF_THEMES): THEME_SCHEMA,
                vol.Optional(CONF_EXTRA_MODULE_URL): vol.All(
                    cv.ensure_list, [cv.string]
                ),
                vol.Optional(CONF_EXTRA_JS_URL_ES5): vol.All(
                    cv.ensure_list, [cv.string]
                ),
                # We no longer use these options.
                vol.Optional(CONF_EXTRA_HTML_URL): cv.match_all,
                vol.Optional(CONF_EXTRA_HTML_URL_ES5): cv.match_all,
                vol.Optional(CONF_JS_VERSION): cv.match_all,
            },
        )
    },
    extra=vol.ALLOW_EXTRA,
)

SERVICE_SET_THEME = "set_theme"
SERVICE_RELOAD_THEMES = "reload_themes"


class Manifest:
    """Manage the manifest.json contents."""

    def __init__(self, data: dict) -> None:
        """Init the manifest manager."""
        self.manifest = data
        self._serialize()

    def __getitem__(self, key: str) -> Any:
        """Return an item in the manifest."""
        return self.manifest[key]

    @property
    def json(self) -> str:
        """Return the serialized manifest."""
        return self._serialized

    def _serialize(self) -> None:
        self._serialized = json_dumps_sorted(self.manifest)

    def update_key(self, key: str, val: str) -> None:
        """Add a keyval to the manifest.json."""
        self.manifest[key] = val
        self._serialize()


MANIFEST_JSON = Manifest(
    {
        "background_color": "#FFFFFF",
        "description": (
            "Home automation platform that puts local control and privacy first."
        ),
        "dir": "ltr",
        "display": "standalone",
        "icons": [
            {
                "src": f"/static/icons/favicon-{size}x{size}.png",
                "sizes": f"{size}x{size}",
                "type": "image/png",
                "purpose": "any",
            }
            for size in (192, 384, 512, 1024)
        ]
        + [
            {
                "src": f"/static/icons/maskable_icon-{size}x{size}.png",
                "sizes": f"{size}x{size}",
                "type": "image/png",
                "purpose": "maskable",
            }
            for size in (48, 72, 96, 128, 192, 384, 512)
        ],
        "screenshots": [
            {
                "src": "/static/images/screenshots/screenshot-1.png",
                "sizes": "413x792",
                "type": "image/png",
            }
        ],
        "lang": "en-US",
        "name": "MenuAI",
        "short_name": "MenuAI",
        "start_url": "/?homescreen=1",
        "id": "/?homescreen=1",
        "theme_color": DEFAULT_THEME_COLOR,
        "prefer_related_applications": True,
        "related_applications": [
            {"platform": "play", "id": "io.menuai.companion.android"}
        ],
    }
)


class UrlManager:
    """Manage urls to be used on the frontend.

    This is abstracted into a class because
    some integrations add a remove these directly
    on menuai.data
    """

    def __init__(
        self,
        on_change: Callable[[str, str], None],
        urls: list[str],
    ) -> None:
        """Init the url manager."""
        self._on_change = on_change
        self.urls = frozenset(urls)

    def add(self, url: str) -> None:
        """Add a url to the set."""
        self.urls = frozenset([*self.urls, url])
        self._on_change("added", url)

    def remove(self, url: str) -> None:
        """Remove a url from the set."""
        self.urls = self.urls - {url}
        self._on_change("removed", url)


class Panel:
    """Abstract class for panels."""

    # Name of the webcomponent
    component_name: str

    # Icon to show in the sidebar
    sidebar_icon: str | None = None

    # Title to show in the sidebar
    sidebar_title: str | None = None

    # Url to show the panel in the frontend
    frontend_url_path: str

    # Config to pass to the webcomponent
    config: dict[str, Any] | None = None

    # If the panel should only be visible to admins
    require_admin = False

    # If the panel is a configuration panel for a integration
    config_panel_domain: str | None = None

    def __init__(
        self,
        component_name: str,
        sidebar_title: str | None,
        sidebar_icon: str | None,
        frontend_url_path: str | None,
        config: dict[str, Any] | None,
        require_admin: bool,
        config_panel_domain: str | None,
    ) -> None:
        """Initialize a built-in panel."""
        self.component_name = component_name
        self.sidebar_title = sidebar_title
        self.sidebar_icon = sidebar_icon
        self.frontend_url_path = frontend_url_path or component_name
        self.config = config
        self.require_admin = require_admin
        self.config_panel_domain = config_panel_domain

    @callback
    def to_response(self) -> PanelResponse:
        """Panel as dictionary."""
        return {
            "component_name": self.component_name,
            "icon": self.sidebar_icon,
            "title": self.sidebar_title,
            "config": self.config,
            "url_path": self.frontend_url_path,
            "require_admin": self.require_admin,
            "config_panel_domain": self.config_panel_domain,
        }


@bind_menuai
@callback
def async_register_built_in_panel(
    menuai: menuai,
    component_name: str,
    sidebar_title: str | None = None,
    sidebar_icon: str | None = None,
    frontend_url_path: str | None = None,
    config: dict[str, Any] | None = None,
    require_admin: bool = False,
    *,
    update: bool = False,
    config_panel_domain: str | None = None,
) -> None:
    """Register a built-in panel."""
    panel = Panel(
        component_name,
        sidebar_title,
        sidebar_icon,
        frontend_url_path,
        config,
        require_admin,
        config_panel_domain,
    )

    panels = menuai.data.setdefault(DATA_PANELS, {})

    if not update and panel.frontend_url_path in panels:
        raise ValueError(f"Overwriting panel {panel.frontend_url_path}")

    panels[panel.frontend_url_path] = panel

    menuai.bus.async_fire(EVENT_PANELS_UPDATED)


@bind_menuai
@callback
def async_remove_panel(
    menuai: menuai, frontend_url_path: str, *, warn_if_unknown: bool = True
) -> None:
    """Remove a built-in panel."""
    panel = menuai.data.get(DATA_PANELS, {}).pop(frontend_url_path, None)

    if panel is None:
        if warn_if_unknown:
            _LOGGER.warning("Removing unknown panel %s", frontend_url_path)
        return

    menuai.bus.async_fire(EVENT_PANELS_UPDATED)


def add_extra_js_url(menuai: menuai, url: str, es5: bool = False) -> None:
    """Register extra js or module url to load.

    This function allows custom integrations to register extra js or module.
    """
    key = DATA_EXTRA_JS_URL_ES5 if es5 else DATA_EXTRA_MODULE_URL
    menuai.data[key].add(url)


def remove_extra_js_url(menuai: menuai, url: str, es5: bool = False) -> None:
    """Remove extra js or module url to load.

    This function allows custom integrations to remove extra js or module.
    """
    key = DATA_EXTRA_JS_URL_ES5 if es5 else DATA_EXTRA_MODULE_URL
    menuai.data[key].remove(url)


def add_manifest_json_key(key: str, val: Any) -> None:
    """Add a keyval to the manifest.json."""
    MANIFEST_JSON.update_key(key, val)


def _frontend_root(dev_repo_path: str | None) -> pathlib.Path:
    """Return root path to the frontend files."""
    if dev_repo_path is not None:
        return pathlib.Path(dev_repo_path) / "menuai_frontend"
    # Keep import here so that we can import frontend without installing reqs
    # pylint: disable-next=import-outside-toplevel
    import menuai_frontend

    return menuai_frontend.where()


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the serving of the frontend."""
    await async_setup_frontend_storage(menuai)
    websocket_api.async_register_command(menuai, websocket_get_icons)
    websocket_api.async_register_command(menuai, websocket_get_panels)
    websocket_api.async_register_command(menuai, websocket_get_themes)
    websocket_api.async_register_command(menuai, websocket_get_translations)
    websocket_api.async_register_command(menuai, websocket_get_version)
    websocket_api.async_register_command(menuai, websocket_subscribe_extra_js)
    menuai.http.register_view(ManifestJSONView())

    conf = config.get(DOMAIN, {})

    for key in (CONF_EXTRA_HTML_URL, CONF_EXTRA_HTML_URL_ES5, CONF_JS_VERSION):
        if key in conf:
            _LOGGER.error(
                "Please remove %s from your frontend config. It is no longer supported",
                key,
            )

    repo_path = conf.get(CONF_FRONTEND_REPO)
    is_dev = repo_path is not None
    root_path = _frontend_root(repo_path)

    static_paths_configs: list[StaticPathConfig] = []

    for path, should_cache in (
        ("service_worker.js", False),
        ("sw-modern.js", False),
        ("sw-modern.js.map", False),
        ("sw-legacy.js", False),
        ("sw-legacy.js.map", False),
        ("robots.txt", False),
        ("onboarding.html", not is_dev),
        ("static", not is_dev),
        ("frontend_latest", not is_dev),
        ("frontend_es5", not is_dev),
    ):
        static_paths_configs.append(
            StaticPathConfig(f"/{path}", str(root_path / path), should_cache)
        )

    static_paths_configs.append(
        StaticPathConfig("/auth/authorize", str(root_path / "authorize.html"), False)
    )
    # https://wicg.github.io/change-password-url/
    menuai.http.register_redirect(
        "/.well-known/change-password", "/profile", redirect_exc=web.HTTPFound
    )

    local = menuai.config.path("www")
    if await menuai.async_add_executor_job(os.path.isdir, local):
        static_paths_configs.append(StaticPathConfig("/local", local, not is_dev))

    await menuai.http.async_register_static_paths(static_paths_configs)
    # Shopping list panel was replaced by todo panel in 2023.11
    menuai.http.register_redirect("/shopping-list", "/todo")

    menuai.http.app.router.register_resource(IndexView(repo_path, menuai))

    async_register_built_in_panel(menuai, "profile")

    async_register_built_in_panel(
        menuai,
        "developer-tools",
        require_admin=True,
        sidebar_title="developer_tools",
        sidebar_icon="menuai:hammer",
    )

    @callback
    def async_change_listener(
        resource_type: str,
        change_type: str,
        url: str,
    ) -> None:
        subscribers = menuai.data[DATA_WS_SUBSCRIBERS]
        json_msg = {
            "change_type": change_type,
            "item": {"type": resource_type, "url": url},
        }
        for connection, msg_id in subscribers:
            connection.send_message(websocket_api.event_message(msg_id, json_msg))

    menuai.data[DATA_EXTRA_MODULE_URL] = UrlManager(
        partial(async_change_listener, "module"), conf.get(CONF_EXTRA_MODULE_URL, [])
    )
    menuai.data[DATA_EXTRA_JS_URL_ES5] = UrlManager(
        partial(async_change_listener, "es5"), conf.get(CONF_EXTRA_JS_URL_ES5, [])
    )
    menuai.data[DATA_WS_SUBSCRIBERS] = set()

    await _async_setup_themes(menuai, conf.get(CONF_THEMES))

    return True


async def _async_setup_themes(
    menuai: menuai, themes: dict[str, Any] | None
) -> None:
    """Set up themes data and services."""
    menuai.data[DATA_THEMES] = themes or {}

    store = menuai.data[DATA_THEMES_STORE] = Store(
        menuai, THEMES_STORAGE_VERSION, THEMES_STORAGE_KEY
    )

    if not (theme_data := await store.async_load()) or not isinstance(theme_data, dict):
        theme_data = {}
    theme_name = theme_data.get(DATA_DEFAULT_THEME, DEFAULT_THEME)
    dark_theme_name = theme_data.get(DATA_DEFAULT_DARK_THEME)

    if theme_name == DEFAULT_THEME or theme_name in menuai.data[DATA_THEMES]:
        menuai.data[DATA_DEFAULT_THEME] = theme_name
    else:
        menuai.data[DATA_DEFAULT_THEME] = DEFAULT_THEME

    if dark_theme_name == DEFAULT_THEME or dark_theme_name in menuai.data[DATA_THEMES]:
        menuai.data[DATA_DEFAULT_DARK_THEME] = dark_theme_name

    @callback
    def update_theme_and_fire_event() -> None:
        """Update theme_color in manifest."""
        name = menuai.data[DATA_DEFAULT_THEME]
        themes = menuai.data[DATA_THEMES]
        if name != DEFAULT_THEME:
            MANIFEST_JSON.update_key(
                "theme_color",
                themes[name].get(
                    "app-header-background-color",
                    themes[name].get(PRIMARY_COLOR, DEFAULT_THEME_COLOR),
                ),
            )
        else:
            MANIFEST_JSON.update_key("theme_color", DEFAULT_THEME_COLOR)
        menuai.bus.async_fire(EVENT_THEMES_UPDATED)

    @callback
    def set_theme(call: ServiceCall) -> None:
        """Set backend-preferred theme."""
        name = call.data[CONF_NAME]
        mode = call.data.get("mode", "light")

        if (
            name not in (DEFAULT_THEME, VALUE_NO_THEME)
            and name not in menuai.data[DATA_THEMES]
        ):
            _LOGGER.warning("Theme %s not found", name)
            return

        light_mode = mode == "light"

        theme_key = DATA_DEFAULT_THEME if light_mode else DATA_DEFAULT_DARK_THEME

        if name == VALUE_NO_THEME:
            to_set = DEFAULT_THEME if light_mode else None
        else:
            _LOGGER.info("Theme %s set as default %s theme", name, mode)
            to_set = name

        menuai.data[theme_key] = to_set
        store.async_delay_save(
            lambda: {
                DATA_DEFAULT_THEME: menuai.data[DATA_DEFAULT_THEME],
                DATA_DEFAULT_DARK_THEME: menuai.data.get(DATA_DEFAULT_DARK_THEME),
            },
            THEMES_SAVE_DELAY,
        )
        update_theme_and_fire_event()

    async def reload_themes(_: ServiceCall) -> None:
        """Reload themes."""
        config = await async_menuai_config_yaml(menuai)
        new_themes = config.get(DOMAIN, {}).get(CONF_THEMES, {})
        menuai.data[DATA_THEMES] = new_themes
        if menuai.data[DATA_DEFAULT_THEME] not in new_themes:
            menuai.data[DATA_DEFAULT_THEME] = DEFAULT_THEME
        if (
            menuai.data.get(DATA_DEFAULT_DARK_THEME)
            and menuai.data.get(DATA_DEFAULT_DARK_THEME) not in new_themes
        ):
            menuai.data[DATA_DEFAULT_DARK_THEME] = None
        update_theme_and_fire_event()

    service.async_register_admin_service(
        menuai,
        DOMAIN,
        SERVICE_SET_THEME,
        set_theme,
        vol.Schema(
            {
                vol.Required(CONF_NAME): cv.string,
                vol.Optional(CONF_MODE): vol.Any("dark", "light"),
            }
        ),
    )

    service.async_register_admin_service(
        menuai, DOMAIN, SERVICE_RELOAD_THEMES, reload_themes
    )


@callback
@lru_cache(maxsize=1)
def _async_render_index_cached(template: jinja2.Template, **kwargs: Any) -> str:
    return template.render(**kwargs)


class IndexView(web_urldispatcher.AbstractResource):
    """Serve the frontend."""

    def __init__(self, repo_path: str | None, menuai: menuai) -> None:
        """Initialize the frontend view."""
        super().__init__(name="frontend:index")
        self.repo_path = repo_path
        self.menuai = menuai
        self._template_cache: jinja2.Template | None = None

    @cached_property
    def canonical(self) -> str:
        """Return resource's canonical path."""
        return "/"

    @cached_property
    def _route(self) -> web_urldispatcher.ResourceRoute:
        """Return the index route."""
        return web_urldispatcher.ResourceRoute("GET", self.get, self)

    def url_for(self, **kwargs: str) -> URL:
        """Construct url for resource with additional params."""
        return URL("/")

    async def resolve(
        self, request: web.Request
    ) -> tuple[web_urldispatcher.UrlMappingMatchInfo | None, set[str]]:
        """Resolve resource.

        Return (UrlMappingMatchInfo, allowed_methods) pair.
        """
        if (
            request.path != "/"
            and (parts := request.rel_url.parts)
            and len(parts) > 1
            and parts[1] not in self.menuai.data[DATA_PANELS]
        ):
            return None, set()

        if request.method != hdrs.METH_GET:
            return None, {"GET"}

        return web_urldispatcher.UrlMappingMatchInfo({}, self._route), {"GET"}

    def add_prefix(self, prefix: str) -> None:
        """Add a prefix to processed URLs.

        Required for subapplications support.
        """

    def get_info(self) -> dict[str, list[str]]:  # type: ignore[override]
        """Return a dict with additional info useful for introspection."""
        panels = self.menuai.data[DATA_PANELS]
        return {"panels": list(panels)}

    def raw_match(self, path: str) -> bool:
        """Perform a raw match against path."""
        return False

    def get_template(self) -> jinja2.Template:
        """Get template."""
        if (tpl := self._template_cache) is None:
            with (_frontend_root(self.repo_path) / "index.html").open(
                encoding="utf8"
            ) as file:
                tpl = jinja2.Template(file.read())

            # Cache template if not running from repository
            if self.repo_path is None:
                self._template_cache = tpl

        return tpl

    async def get(self, request: web.Request) -> web.Response:
        """Serve the index page for panel pages."""
        menuai = request.app[KEY_menuai]

        if not onboarding.async_is_onboarded(menuai):
            return web.Response(status=302, headers={"location": "/onboarding.html"})

        template = self._template_cache or await menuai.async_add_executor_job(
            self.get_template
        )

        extra_modules: frozenset[str]
        extra_js_es5: frozenset[str]
        if menuai.config.safe_mode:
            extra_modules = frozenset()
            extra_js_es5 = frozenset()
        else:
            extra_modules = menuai.data[DATA_EXTRA_MODULE_URL].urls
            extra_js_es5 = menuai.data[DATA_EXTRA_JS_URL_ES5].urls

        response = web.Response(
            text=_async_render_index_cached(
                template,
                theme_color=MANIFEST_JSON["theme_color"],
                extra_modules=extra_modules,
                extra_js_es5=extra_js_es5,
            ),
            content_type="text/html",
        )
        response.enable_compression()
        return response

    def __len__(self) -> int:
        """Return length of resource."""
        return 1

    def __iter__(self) -> Iterator[web_urldispatcher.ResourceRoute]:
        """Iterate over routes."""
        return iter([self._route])


class ManifestJSONView(menuaiView):
    """View to return a manifest.json."""

    requires_auth = False
    url = "/manifest.json"
    name = "manifestjson"

    @callback
    def get(self, request: web.Request) -> web.Response:
        """Return the manifest.json."""
        response = web.Response(
            text=MANIFEST_JSON.json, content_type="application/manifest+json"
        )
        response.enable_compression()
        return response


@websocket_api.websocket_command(
    {
        "type": "frontend/get_icons",
        vol.Required("category"): vol.In({"entity", "entity_component", "services"}),
        vol.Optional("integration"): vol.All(cv.ensure_list, [str]),
    }
)
@websocket_api.async_response
async def websocket_get_icons(
    menuai: menuai, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Handle get icons command."""
    resources = await async_get_icons(
        menuai,
        msg["category"],
        msg.get("integration"),
    )
    connection.send_message(
        websocket_api.result_message(msg["id"], {"resources": resources})
    )


@callback
@websocket_api.websocket_command({"type": "get_panels"})
def websocket_get_panels(
    menuai: menuai, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Handle get panels command."""
    user_is_admin = connection.user.is_admin
    panels = {
        panel_key: panel.to_response()
        for panel_key, panel in connection.menuai.data[DATA_PANELS].items()
        if user_is_admin or not panel.require_admin
    }

    connection.send_message(websocket_api.result_message(msg["id"], panels))


@callback
@websocket_api.websocket_command({"type": "frontend/get_themes"})
def websocket_get_themes(
    menuai: menuai, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Handle get themes command."""
    if menuai.config.recovery_mode or menuai.config.safe_mode:
        connection.send_message(
            websocket_api.result_message(
                msg["id"],
                {
                    "themes": {},
                    "default_theme": "default",
                },
            )
        )
        return

    connection.send_message(
        websocket_api.result_message(
            msg["id"],
            {
                "themes": menuai.data[DATA_THEMES],
                "default_theme": menuai.data[DATA_DEFAULT_THEME],
                "default_dark_theme": menuai.data.get(DATA_DEFAULT_DARK_THEME),
            },
        )
    )


@websocket_api.websocket_command(
    {
        "type": "frontend/get_translations",
        vol.Required("language"): str,
        vol.Required("category"): str,
        vol.Optional("integration"): vol.All(cv.ensure_list, [str]),
        vol.Optional("config_flow"): bool,
    }
)
@websocket_api.async_response
async def websocket_get_translations(
    menuai: menuai, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Handle get translations command."""
    resources = await async_get_translations(
        menuai,
        msg["language"],
        msg["category"],
        msg.get("integration"),
        msg.get("config_flow"),
    )
    connection.send_message(
        websocket_api.result_message(msg["id"], {"resources": resources})
    )


@websocket_api.websocket_command({"type": "frontend/get_version"})
@websocket_api.async_response
async def websocket_get_version(
    menuai: menuai, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Handle get version command."""
    integration = await async_get_integration(menuai, "frontend")

    frontend = None

    for req in integration.requirements:
        if req.startswith("home-assistant-frontend=="):
            frontend = req.removeprefix("home-assistant-frontend==")

    if frontend is None:
        connection.send_error(msg["id"], "unknown_version", "Version not found")
    else:
        connection.send_result(msg["id"], {"version": frontend})


@callback
@websocket_api.websocket_command({"type": "frontend/subscribe_extra_js"})
def websocket_subscribe_extra_js(
    menuai: menuai, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Subscribe to URL manager updates."""

    subscribers = menuai.data[DATA_WS_SUBSCRIBERS]
    subscribers.add((connection, msg["id"]))

    @callback
    def cancel_subscription() -> None:
        subscribers.remove((connection, msg["id"]))

    connection.subscriptions[msg["id"]] = cancel_subscription
    connection.send_message(websocket_api.result_message(msg["id"]))


class PanelResponse(TypedDict):
    """Represent the panel response type."""

    component_name: str
    icon: str | None
    title: str | None
    config: dict[str, Any] | None
    url_path: str
    require_admin: bool
    config_panel_domain: str | None
