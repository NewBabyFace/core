"""Provide persistent configuration for the menuaiio integration."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Required, Self, TypedDict

from menuai.core import menuai, callback
from menuai.helpers.storage import Store
from menuai.helpers.typing import UNDEFINED, UndefinedType

from .const import DOMAIN

STORE_DELAY_SAVE = 30
STORAGE_KEY = DOMAIN
STORAGE_VERSION = 1
STORAGE_VERSION_MINOR = 1


class menuaiioConfig:
    """Handle update config."""

    def __init__(self, menuai: menuai) -> None:
        """Initialize update config."""
        self.data = menuaiioConfigData(
            menuaiio_user=None,
            update_config=menuaiioUpdateConfig(),
        )
        self._menuai = menuai
        self._store = menuaiioConfigStore(menuai, self)

    async def load(self) -> None:
        """Load config."""
        if not (store_data := await self._store.load()):
            return
        self.data = menuaiioConfigData.from_dict(store_data)

    @callback
    def update(
        self,
        *,
        menuaiio_user: str | UndefinedType = UNDEFINED,
        update_config: menuaiioUpdateParametersDict | UndefinedType = UNDEFINED,
    ) -> None:
        """Update config."""
        if menuaiio_user is not UNDEFINED:
            self.data.menuaiio_user = menuaiio_user
        if update_config is not UNDEFINED:
            self.data.update_config = replace(self.data.update_config, **update_config)

        self._store.save()


@dataclass(kw_only=True)
class menuaiioConfigData:
    """Represent loaded update config data."""

    menuaiio_user: str | None
    update_config: menuaiioUpdateConfig

    @classmethod
    def from_dict(cls, data: StoredmenuaiioConfig) -> Self:
        """Initialize update config data from a dict."""
        if update_data := data.get("update_config"):
            update_config = menuaiioUpdateConfig(
                add_on_backup_before_update=update_data["add_on_backup_before_update"],
                add_on_backup_retain_copies=update_data["add_on_backup_retain_copies"],
                core_backup_before_update=update_data["core_backup_before_update"],
            )
        else:
            update_config = menuaiioUpdateConfig()
        return cls(
            menuaiio_user=data["menuaiio_user"],
            update_config=update_config,
        )

    def to_dict(self) -> StoredmenuaiioConfig:
        """Convert update config data to a dict."""
        return StoredmenuaiioConfig(
            menuaiio_user=self.menuaiio_user,
            update_config=self.update_config.to_dict(),
        )


@dataclass(kw_only=True)
class menuaiioUpdateConfig:
    """Represent the backup retention configuration."""

    add_on_backup_before_update: bool = False
    add_on_backup_retain_copies: int = 1
    core_backup_before_update: bool = False

    def to_dict(self) -> StoredmenuaiioUpdateConfig:
        """Convert backup retention configuration to a dict."""
        return StoredmenuaiioUpdateConfig(
            add_on_backup_before_update=self.add_on_backup_before_update,
            add_on_backup_retain_copies=self.add_on_backup_retain_copies,
            core_backup_before_update=self.core_backup_before_update,
        )


class menuaiioUpdateParametersDict(TypedDict, total=False):
    """Represent the parameters for update."""

    add_on_backup_before_update: bool
    add_on_backup_retain_copies: int
    core_backup_before_update: bool


class menuaiioConfigStore:
    """Store menuaiio config."""

    def __init__(self, menuai: menuai, config: menuaiioConfig) -> None:
        """Initialize the menuaiio config store."""
        self._menuai = menuai
        self._config = config
        self._store: Store[StoredmenuaiioConfig] = Store(
            menuai, STORAGE_VERSION, STORAGE_KEY, minor_version=STORAGE_VERSION_MINOR
        )

    async def load(self) -> StoredmenuaiioConfig | None:
        """Load the store."""
        return await self._store.async_load()

    @callback
    def save(self) -> None:
        """Save config."""
        self._store.async_delay_save(self._data_to_save, STORE_DELAY_SAVE)

    @callback
    def _data_to_save(self) -> StoredmenuaiioConfig:
        """Return data to save."""
        return self._config.data.to_dict()


class StoredmenuaiioConfig(TypedDict, total=False):
    """Represent the stored menuaiio config."""

    menuaiio_user: Required[str | None]
    update_config: StoredmenuaiioUpdateConfig


class StoredmenuaiioUpdateConfig(TypedDict):
    """Represent the stored update config."""

    add_on_backup_before_update: bool
    add_on_backup_retain_copies: int
    core_backup_before_update: bool
