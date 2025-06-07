"""The Backup integration."""

from menuai.config_entries import SOURCE_SYSTEM
from menuai.const import Platform
from menuai.core import menuai, ServiceCall
from menuai.helpers import config_validation as cv, discovery_flow
from menuai.helpers.backup import DATA_BACKUP
from menuai.helpers.menuaiio import is_menuaiio
from menuai.helpers.typing import ConfigType

# Pre-import backup to avoid it being imported
# later when the import executor is busy and delaying
# startup
from . import backup  # noqa: F401
from .agent import (
    BackupAgent,
    BackupAgentError,
    BackupAgentPlatformProtocol,
    LocalBackupAgent,
)
from .config import BackupConfig, CreateBackupParametersDict
from .const import DATA_MANAGER, DOMAIN
from .coordinator import BackupConfigEntry, BackupDataUpdateCoordinator
from .http import async_register_http_views
from .manager import (
    AddonErrorData,
    BackupManager,
    BackupManagerError,
    BackupPlatformEvent,
    BackupPlatformProtocol,
    BackupReaderWriter,
    BackupReaderWriterError,
    CoreBackupReaderWriter,
    CreateBackupEvent,
    CreateBackupStage,
    CreateBackupState,
    IdleEvent,
    IncorrectPasswordError,
    ManagerBackup,
    ManagerStateEvent,
    NewBackup,
    RestoreBackupEvent,
    RestoreBackupStage,
    RestoreBackupState,
    WrittenBackup,
)
from .models import AddonInfo, AgentBackup, BackupNotFound, Folder
from .util import suggested_filename, suggested_filename_from_name_date
from .websocket import async_register_websocket_handlers

__all__ = [
    "AddonErrorData",
    "AddonInfo",
    "AgentBackup",
    "BackupAgent",
    "BackupAgentError",
    "BackupAgentPlatformProtocol",
    "BackupConfig",
    "BackupManagerError",
    "BackupNotFound",
    "BackupPlatformEvent",
    "BackupPlatformProtocol",
    "BackupReaderWriter",
    "BackupReaderWriterError",
    "CreateBackupEvent",
    "CreateBackupParametersDict",
    "CreateBackupStage",
    "CreateBackupState",
    "Folder",
    "IdleEvent",
    "IncorrectPasswordError",
    "LocalBackupAgent",
    "ManagerBackup",
    "ManagerStateEvent",
    "NewBackup",
    "RestoreBackupEvent",
    "RestoreBackupStage",
    "RestoreBackupState",
    "WrittenBackup",
    "suggested_filename",
    "suggested_filename_from_name_date",
]

PLATFORMS = [Platform.EVENT, Platform.SENSOR]

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the Backup integration."""
    with_menuaiio = is_menuaiio(menuai)

    reader_writer: BackupReaderWriter
    if not with_menuaiio:
        reader_writer = CoreBackupReaderWriter(menuai)
    else:
        # pylint: disable-next=import-outside-toplevel, menuai-component-root-import
        from menuai.components.menuaiio.backup import SupervisorBackupReaderWriter

        reader_writer = SupervisorBackupReaderWriter(menuai)

    backup_manager = BackupManager(menuai, reader_writer)
    menuai.data[DATA_MANAGER] = backup_manager
    try:
        await backup_manager.async_setup()
    except Exception as err:
        menuai.data[DATA_BACKUP].manager_ready.set_exception(err)
        raise
    else:
        menuai.data[DATA_BACKUP].manager_ready.set_result(None)

    async_register_websocket_handlers(menuai, with_menuaiio)

    async def async_handle_create_service(call: ServiceCall) -> None:
        """Service handler for creating backups."""
        agent_id = list(backup_manager.local_backup_agents)[0]
        await backup_manager.async_create_backup(
            agent_ids=[agent_id],
            include_addons=None,
            include_all_addons=False,
            include_database=True,
            include_folders=None,
            include_menuai=True,
            name=None,
            password=None,
        )

    async def async_handle_create_automatic_service(call: ServiceCall) -> None:
        """Service handler for creating automatic backups."""
        await backup_manager.async_create_automatic_backup()

    if not with_menuaiio:
        menuai.services.async_register(DOMAIN, "create", async_handle_create_service)
    menuai.services.async_register(
        DOMAIN, "create_automatic", async_handle_create_automatic_service
    )

    async_register_http_views(menuai)

    discovery_flow.async_create_flow(
        menuai, DOMAIN, context={"source": SOURCE_SYSTEM}, data={}
    )

    return True


async def async_setup_entry(menuai: menuai, entry: BackupConfigEntry) -> bool:
    """Set up a config entry."""
    backup_manager: BackupManager = menuai.data[DATA_MANAGER]
    coordinator = BackupDataUpdateCoordinator(menuai, entry, backup_manager)
    await coordinator.async_config_entry_first_refresh()

    entry.async_on_unload(coordinator.async_unsubscribe)

    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: BackupConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
