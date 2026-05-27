from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterable, Literal, Sequence, final

from LSP.plugin import ClientConfig
from more_itertools import unique_everseen

from ..constants import SERVER_SETTING_ANALYSIS_EXTRAPATHS, SERVER_SETTING_DEV_ENVIRONMENT
from ..log import log_debug


class BaseDevEnvironmentHandler(ABC):
    def __init__(self, *, package_storage_path: str | Path, workspace_folders: Sequence[str]) -> None:
        self.package_storage_path = Path(package_storage_path)
        """The language server directory."""
        self.workspace_folders = workspace_folders
        """The workspace folders."""

    @classmethod
    @abstractmethod
    def name(cls) -> str:
        """The name of this environment."""

    @final
    @classmethod
    def get_dev_environment_subsetting(cls, config: ClientConfig, subkey: str) -> Any:
        """Gets the sub-setting of `XXX.dev_environment_NAME.SUBKEY`."""
        return config.settings.get(f"{SERVER_SETTING_DEV_ENVIRONMENT}_{cls.name()}.{subkey}")

    @classmethod
    def can_support(cls, dev_environment: str) -> bool:
        """Check if this class support the given `dev_environment`."""
        return cls.name() == dev_environment

    @final
    def handle(self, *, config: ClientConfig) -> None:
        """Handle this environment."""
        self.handle_(config=config)

    @abstractmethod
    def handle_(self, *, config: ClientConfig) -> None:
        """Handle this environment. (subclass)"""

    def _inject_extra_paths(
        self,
        *,
        config: ClientConfig,
        paths: Iterable[str | Path],
        operation: Literal["append", "prepend", "replace"] = "append",
    ) -> None:
        """Injects the given `paths` to `XXX.analysis.extraPaths` setting."""
        current_paths: list[str] = config.settings.get(SERVER_SETTING_ANALYSIS_EXTRAPATHS) or []
        extra_paths = list(map(str, paths))
        if operation == "prepend":
            next_paths = extra_paths + current_paths
        elif operation == "append":
            next_paths = current_paths + extra_paths
        elif operation == "replace":
            next_paths = extra_paths
        else:
            raise ValueError(f"Invalid operation: {operation}")

        next_paths = list(unique_everseen(next_paths, key=Path))  # deduplication
        log_debug(f'Due to "dev_environment", new "analysis.extraPaths" is ({operation = }): {next_paths}')
        config.settings.set(SERVER_SETTING_ANALYSIS_EXTRAPATHS, next_paths)
