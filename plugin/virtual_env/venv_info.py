from __future__ import annotations

import configparser
import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generator, TypedDict, final

from typing_extensions import Self

from ..utils import run_shell_command


def list_venv_info_classes() -> Generator[type[BaseVenvInfo], None, None]:
    """
    Lists all virtual environment information classes.

    The order matters because they will be used for testing one by one.
    """
    yield Pep405VenvInfo
    yield CondaVenvInfo


@dataclass
class VenvInfoMeta:
    finder_name: str = ""
    """The name of the virtual environment finder."""


@dataclass
class BaseVenvInfo(ABC):
    """The information of the virtual environment."""

    venv_dir: Path
    """The path of the virtual environment directory."""

    prompt: str = ""
    """The prompt of the virtual environment."""
    python_version: str = ""
    """The Python version of the virtual environment."""

    meta: VenvInfoMeta = field(default_factory=VenvInfoMeta)
    """The metadata which is not related to venv."""

    @property
    def python_executable(self) -> Path:
        """The path of the Python executable of the virtual environment."""
        if os.name == "nt":
            return self.venv_dir / "Scripts/python.exe"
        return self.venv_dir / "bin/python"

    @abstractmethod
    def is_valid(self) -> bool:
        """Checks if this virtual environment is valid."""

    @abstractmethod
    def refresh_derived_attributes(self) -> None:
        """Refreshes the derived attributes."""

    @classmethod
    def from_python_executable(cls, python_executable: str | Path) -> Self | None:
        """Create an instance from the Python executable path."""
        try:
            venv_dir = Path(python_executable).parents[1]
        except IndexError:
            return None
        return cls.from_venv_dir(venv_dir)

    @final
    @classmethod
    def from_venv_dir(cls, venv_dir: str | Path) -> Self | None:
        """Create an instance from the virtual environment directory."""
        try:
            venv_dir = Path(venv_dir).expanduser().resolve()
        except PermissionError:
            return None

        if not (venv_info := cls(venv_dir=venv_dir)).is_valid():
            return None

        venv_info.refresh_derived_attributes()
        return venv_info


class CondaInfoDict(TypedDict):
    active_prefix: str
    active_prefix_name: str
    av_data_dir: str
    av_metadata_url_base: str | None
    channels: list[str]
    conda_build_version: str
    conda_env_version: str
    conda_location: str
    conda_prefix: str
    conda_shlvl: int
    conda_version: str
    config_files: list[str]
    default_prefix: str
    env_vars: dict[str, str]
    envs: list[str]
    envs_dirs: list[str]
    netrc_file: str | None
    offline: bool
    pkgs_dirs: list[str]
    platform: str
    python_version: str
    rc_path: str
    requests_version: str
    root_prefix: str
    root_writable: bool
    site_dirs: list[str]
    solver: dict[str, Any]
    sys_rc_path: str
    user_agent: str
    user_rc_path: str
    virtual_pkgs: list[list[str]]


class CondaVenvInfo(BaseVenvInfo):
    """Venv information for Conda virtual environment."""

    @property
    def conda_meta_path(self) -> Path:
        """The path of the `conda-meta` directory of the virtual environment."""
        return self.venv_dir / "conda-meta"

    def is_valid(self) -> bool:
        try:
            return self.python_executable.is_file() and self.conda_meta_path.is_dir()
        except PermissionError:
            return False

    def refresh_derived_attributes(self) -> None:
        if not (conda_info := self.get_conda_info()):
            return

        self.prompt = conda_info.get("active_prefix_name", "")
        self.python_version = (
            conda_info.get("python_version", "")
            .replace(".alpha.", "a")
            .replace(".beta.", "b")
            .replace(".candidate.", "rc")
            .partition(".final.")[0]
        )

    @staticmethod
    def get_conda_info() -> CondaInfoDict | None:
        """Get the Conda venv information."""
        if not (output := run_shell_command("conda info --json")):
            return None
        stdout, _, _ = output

        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            return None


class Pep405VenvInfo(BaseVenvInfo):
    """Venv information for PEP 405 (https://peps.python.org/pep-0405/)"""

    @property
    def pyvenv_cfg_path(self) -> Path:
        """The path of the `pyvenv.cfg` file of the virtual environment."""
        return self.venv_dir / "pyvenv.cfg"

    def is_valid(self) -> bool:
        try:
            return self.python_executable.is_file() and self.pyvenv_cfg_path.is_file()
        except PermissionError:
            return False

    def refresh_derived_attributes(self) -> None:
        pyvenv_cfg = self.parse_pyvenv_cfg(self.pyvenv_cfg_path)

        self.prompt = pyvenv_cfg.get("prompt", "") or self.venv_dir.name
        # "venv" module uses "version" and "uv" utility uses "version_info"
        self.python_version = pyvenv_cfg.get("version", "") or pyvenv_cfg.get("version_info", "")

    @classmethod
    def from_pyvenv_cfg_file(cls, pyvenv_cfg_file: str | Path) -> Self | None:
        try:
            venv_dir = Path(pyvenv_cfg_file).parents[0]
        except IndexError:
            return None
        return cls.from_venv_dir(venv_dir)

    @staticmethod
    def parse_pyvenv_cfg(pyvenv_cfg: Path) -> dict[str, str]:
        # value of these keys are expected to be a string
        config = configparser.ConfigParser()
        try:
            content = pyvenv_cfg.read_text(encoding="utf-8")
            config.read_string(f"[USER]\n{content}")
        except Exception:
            return {}
        return dict(config.items("USER"))
