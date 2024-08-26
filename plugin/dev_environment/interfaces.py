from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterable, Sequence, final

from LSP.plugin.core.collections import DottedDict

from ..constants import SERVER_SETTING_ANALYSIS_EXTRAPATHS, SERVER_SETTING_DEV_ENVIRONMENT
from ..log import log_info
from ..utils import camel_to_snake, remove_suffix


class BaseDevEnvironmentHandler(ABC):
    def __init__(
        self,
        *,
        server_dir: str | Path,
        workspace_folders: Sequence[str],
    ) -> None:
        self.server_dir = Path(server_dir)
        """The language server directory."""
        self.workspace_folders = workspace_folders
        """The workspace folders."""

    @classmethod
    def name(cls) -> str:
        """The name of this environment."""
        return camel_to_snake(remove_suffix(cls.__name__, "DevEnvironmentHandler"))

    @final
    @classmethod
    def get_dev_environment_subsetting(cls, settings: DottedDict, subkey: str) -> Any:
        """Gets the sub-setting of `XXX.dev_environment.CLS_NAME.SUBKEY`."""
        return settings.get(f"{SERVER_SETTING_DEV_ENVIRONMENT}_{cls.name()}.{subkey}")

    @classmethod
    def can_support(cls, dev_environment: str) -> bool:
        """Check if this class support the given `dev_environment`."""
        return cls.name() == dev_environment

    @abstractmethod
    def handle(self, *, settings: DottedDict) -> None:
        """Handle this environment."""

    def _inject_extra_paths(self, *, settings: DottedDict, paths: Iterable[str | Path]) -> None:
        """Appends the given `paths` to `XXX.analysis.extraPaths` setting."""
        extra_paths: list[str] = settings.get(SERVER_SETTING_ANALYSIS_EXTRAPATHS) or []
        extra_paths.extend(map(str, paths))
        log_info(f"Adding extra analysis paths: {paths}")
        settings.set(SERVER_SETTING_ANALYSIS_EXTRAPATHS, extra_paths)
