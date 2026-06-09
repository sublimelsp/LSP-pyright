from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterable, Literal, Sequence, final

from LSP.plugin import DottedDict
from more_itertools import unique_everseen

from ..constants import SERVER_SETTING_ANALYSIS_EXTRAPATHS, SERVER_SETTING_DEV_ENVIRONMENT
from ..log import log_debug


class BaseDevEnvironmentHandler(ABC):
    def __init__(self, *, package_storage_path: Path, workspace_folders: Sequence[str]) -> None:
        self.package_storage_path = package_storage_path
        """The language server directory."""
        self.workspace_folders = workspace_folders
        """The workspace folders."""

    @classmethod
    @abstractmethod
    def name(cls) -> str:
        """The name of this environment."""

    @final
    @classmethod
    def get_dev_environment_subsetting(cls, settings: DottedDict, subkey: str) -> Any:
        """Gets the sub-setting of `XXX.dev_environment_NAME.SUBKEY`."""
        return settings.get(f"{SERVER_SETTING_DEV_ENVIRONMENT}_{cls.name()}.{subkey}")

    @classmethod
    def can_support(cls, dev_environment: str) -> bool:
        """Check if this class support the given `dev_environment`."""
        return cls.name() == dev_environment

    @final
    def resolve_extra_paths(self, *, settings: DottedDict) -> list[str]:
        """Returns resolved `extraPaths` including `current_paths` for the environment."""
        return self.resolve_extra_paths_(settings=settings)

    @abstractmethod
    def resolve_extra_paths_(self, *, settings: DottedDict) -> list[str]:
        """Handle this environment. (subclass)"""

    def _resolve_paths(
        self,
        *,
        settings: DottedDict,
        paths: Iterable[str | Path],
        operation: Literal["append", "prepend", "replace"] = "append",
    ) -> list[str]:
        """Injects the given `paths` to `XXX.analysis.extraPaths` setting."""
        current_paths: list[str] = settings.get(SERVER_SETTING_ANALYSIS_EXTRAPATHS) or []
        extra_paths = list(map(str, paths))
        if operation == "prepend":
            resolved_paths = extra_paths + current_paths
        elif operation == "append":
            resolved_paths = current_paths + extra_paths
        elif operation == "replace":
            resolved_paths = extra_paths
        else:
            raise ValueError(f"Invalid operation: {operation}")

        resolved_paths = list(map(str, unique_everseen(resolved_paths, key=Path)))  # deduplication
        log_debug(f'Due to "dev_environment", new "analysis.extraPaths" is ({operation = }): {resolved_paths}')
        return resolved_paths
