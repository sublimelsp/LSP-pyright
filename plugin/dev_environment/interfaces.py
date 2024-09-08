from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterable, Sequence, final

from LSP.plugin.core.collections import DottedDict

from ..constants import SERVER_SETTING_ANALYSIS_EXTRAPATHS, SERVER_SETTING_DEV_ENVIRONMENT
from ..log import log_info
from ..utils import camel_to_snake, remove_suffix
from ..virtual_env.venv_info import BaseVenvInfo


class BaseDevEnvironmentHandler(ABC):
    def __init__(
        self,
        *,
        server_dir: str | Path,
        workspace_folders: Sequence[str],
        venv_info: BaseVenvInfo | None = None,
    ) -> None:
        self.server_dir = Path(server_dir)
        """The language server directory."""
        self.workspace_folders = workspace_folders
        """The workspace folders."""
        self.venv_info = venv_info
        """The virtual environment information."""

    @classmethod
    def name(cls) -> str:
        """The name of this environment."""
        return camel_to_snake(remove_suffix(cls.__name__, "DevEnvironmentHandler"))

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
    def handle(self, *, settings: DottedDict) -> None:
        """Handle this environment."""
        self.handle_(settings=settings)

        if self.venv_info:
            self._inject_extra_paths(settings=settings, paths=(self.venv_info.site_packages_dir,), prepend=True)

    @abstractmethod
    def handle_(self, *, settings: DottedDict) -> None:
        """Handle this environment. (subclass)"""

    def _inject_extra_paths(
        self,
        *,
        settings: DottedDict,
        paths: Iterable[str | Path],
        prepend: bool = False,
    ) -> None:
        """Injects the given `paths` to `XXX.analysis.extraPaths` setting."""
        current_paths: list[str] = settings.get(SERVER_SETTING_ANALYSIS_EXTRAPATHS) or []
        extra_paths = list(map(str, paths))
        if prepend:
            next_paths = extra_paths + current_paths
        else:
            next_paths = current_paths + extra_paths
        log_info(f"Adding extra analysis paths ({prepend = }): {paths}")
        settings.set(SERVER_SETTING_ANALYSIS_EXTRAPATHS, next_paths)
