from __future__ import annotations

import configparser
import os
import shutil
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Any, Generator, Iterable, Mapping, Sequence, final

from more_itertools import first_true
from typing_extensions import Self

from .log import log_error
from .utils import camel_to_snake, get_default_startupinfo, iterate_by_line, remove_suffix


def find_venv_by_finder_names(finder_names: Sequence[str], *, project_dir: Path) -> VenvInfo | None:
    if isinstance(finder_names, str):
        finder_names = (finder_names,)

    for finder_name in finder_names:
        if (
            (finder_cls := find_finder_class_by_name(finder_name))
            and finder_cls.can_support(project_dir)
            and (venv_info := finder_cls(project_dir).find_venv())
        ):
            return venv_info
    return None


@lru_cache
def find_finder_class_by_name(name: str) -> type[BaseVenvFinder] | None:
    """Finds the virtual environment finder class by its name."""
    return get_finder_name_mapping().get(name)


@lru_cache
def get_finder_name_mapping() -> Mapping[str, type[BaseVenvFinder]]:
    """Returns a mapping of virtual environment finder names to their classes."""
    return MappingProxyType({finder_cls.name(): finder_cls for finder_cls in list_venv_finder_classes()})


def list_venv_finder_classes() -> Generator[type[BaseVenvFinder], None, None]:
    """Lists all virtual environment finder classes. The order matters."""
    yield LocalDotVenvVenvFinder
    yield EnvVarCondaPrefixVenvFinder
    yield EnvVarVirtualEnvVenvFinder
    yield RyeVenvFinder
    yield PoetryVenvFinder
    yield PdmVenvFinder
    yield HatchVenvFinder
    yield PipenvVenvFinder
    yield PyenvVenvFinder
    yield AnySubdirectoryVenvFinder


@dataclass
class VenvInfoCache:
    pyvenv_cfg: dict[str, Any] = field(default_factory=dict)
    """The parsed results of the `pyvenv.cfg` file."""


@dataclass
class VenvInfoMeta:
    finder_name: str = ""
    """The name of the virtual environment finder."""


@dataclass(frozen=True)
class VenvInfo:
    """The information of the virtual environment."""

    venv_dir: Path
    """The path of the virtual environment directory."""

    cache: VenvInfoCache = field(default_factory=VenvInfoCache)
    """The cache."""
    meta: VenvInfoMeta = field(default_factory=VenvInfoMeta)
    """The metadata."""

    @property
    def prompt(self) -> str:
        """The prompt of the virtual environment."""
        if prompt := str(self.cache.pyvenv_cfg.get("prompt", "")):
            return prompt
        return self.venv_dir.name

    @property
    def python_executable(self) -> Path:
        """The path of the Python executable of the virtual environment."""
        if os.name == "nt":
            return self.venv_dir / "Scripts/python.exe"
        return self.venv_dir / "bin/python"

    @property
    def python_version(self) -> str:
        """The Python version of the virtual environment."""
        # "venv" module uses "version"
        if version := str(self.cache.pyvenv_cfg.get("version", "")):
            return version
        # "uv" utility uses "version_info"
        if version := str(self.cache.pyvenv_cfg.get("version_info", "")):
            return version
        return ""

    @property
    def pyvenv_cfg_path(self) -> Path:
        """The path of the `pyvenv.cfg` file of the virtual environment."""
        return self.venv_dir / "pyvenv.cfg"

    def is_valid(self) -> bool:
        """Checks if this virtual environment is valid."""
        try:
            return self.venv_dir.is_dir() and self.pyvenv_cfg_path.is_file() and self.python_executable.is_file()
        except PermissionError:
            return False

    def refresh_cache(self) -> None:
        """Refreshes cached property values."""
        self.cache.pyvenv_cfg = self.parse_pyvenv_cfg(self.pyvenv_cfg_path)

    @classmethod
    def from_venv_dir(cls, venv_dir: str | Path) -> Self | None:
        try:
            venv_dir = Path(venv_dir).expanduser().resolve()
        except PermissionError:
            return None

        if (venv_info := cls(venv_dir=venv_dir)).is_valid():
            venv_info.refresh_cache()
            return venv_info
        return None

    @classmethod
    def from_python_executable(cls, python_executable: str | Path) -> Self | None:
        try:
            venv_dir = Path(python_executable).parents[1]
        except IndexError:
            return None
        return cls.from_venv_dir(venv_dir)

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


class BaseVenvFinder(ABC):
    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir
        """The project root directory."""

    @final
    @classmethod
    def name(cls) -> str:
        return camel_to_snake(remove_suffix(cls.__name__, "VenvFinder"))

    @final
    @classmethod
    def can_support(cls, project_dir: Path) -> bool:
        """Check if this class support the given `project_dir`."""
        try:
            return cls._can_support(project_dir)
        except PermissionError:
            return False

    @final
    def find_venv(self) -> VenvInfo | None:
        """Find the virtual environment."""
        try:
            venv_info = self._find_venv()
        except PermissionError:
            return None

        if venv_info:
            venv_info.meta.finder_name = self.name()
            return venv_info
        return None

    @classmethod
    @abstractmethod
    def _can_support(cls, project_dir: Path) -> bool:
        """Check if this class support the given `project_dir`. Implement this method by the subclass."""

    @abstractmethod
    def _find_venv(self) -> VenvInfo | None:
        """Find the virtual environment. Implement this method by the subclass."""

    @staticmethod
    def _find_from_venv_dirs(venv_dirs: Iterable[Path]) -> VenvInfo | None:
        def _filtered_candidates() -> Generator[Path, None, None]:
            for venv_dir in venv_dirs:
                try:
                    if venv_dir.is_dir():
                        yield venv_dir
                except PermissionError:
                    pass

        return first_true(map(VenvInfo.from_venv_dir, _filtered_candidates()))

    @staticmethod
    def _run_shell_command(command: str, *, cwd: Path | None = None) -> tuple[str, str, int] | None:
        try:
            proc = subprocess.Popen(
                command,
                cwd=cwd,
                shell=True,
                startupinfo=get_default_startupinfo(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
            stdout, stderr = map(str.rstrip, proc.communicate())
        except Exception as e:
            log_error(f"Failed running command ({command}): {e}")
            return None

        if stderr:
            log_error(f"Failed running command ({command}): {stderr}")

        return stdout, stderr, proc.returncode


class AnySubdirectoryVenvFinder(BaseVenvFinder):
    """Finds the virtual environment with any subdirectory."""

    @classmethod
    def _can_support(cls, project_dir: Path) -> bool:
        return True

    def _find_venv(self) -> VenvInfo | None:
        return self._find_from_venv_dirs(self.project_dir.iterdir())


class EnvVarCondaPrefixVenvFinder(BaseVenvFinder):
    """
    Finds the virtual environment using the `CONDA_PREFIX` environment variable.

    @see https://github.com/conda/conda
    """

    @classmethod
    def _can_support(cls, project_dir: Path) -> bool:
        return "CONDA_PREFIX" in os.environ

    def _find_venv(self) -> VenvInfo | None:
        return VenvInfo.from_venv_dir(os.environ["CONDA_PREFIX"])


class EnvVarVirtualEnvVenvFinder(BaseVenvFinder):
    """
    Finds the virtual environment using the `VIRTUAL_ENV` environment variable.

    @see https://docs.python.org/library/venv.html
    """

    @classmethod
    def _can_support(cls, project_dir: Path) -> bool:
        return "VIRTUAL_ENV" in os.environ

    def _find_venv(self) -> VenvInfo | None:
        return VenvInfo.from_venv_dir(os.environ["VIRTUAL_ENV"])


class LocalDotVenvVenvFinder(BaseVenvFinder):
    """
    Finds the virtual environment `.venv` or `venv` directory.

    @see https://docs.python.org/library/venv.html
    """

    @classmethod
    def _can_support(cls, project_dir: Path) -> bool:
        return True

    def _find_venv(self) -> VenvInfo | None:
        return self._find_from_venv_dirs((
            self.project_dir / ".venv",
            self.project_dir / "venv",
        ))


class HatchVenvFinder(BaseVenvFinder):
    """
    Finds the virtual environment using `hatch`.

    @see https://github.com/pypa/hatch
    """

    @classmethod
    def _can_support(cls, project_dir: Path) -> bool:
        return bool(shutil.which("hatch"))

    def _find_venv(self) -> VenvInfo | None:
        # "hatch env find" will always provide a calculated path, where the hatch-managed venv should be at
        if not (output := self._run_shell_command("hatch env find", cwd=self.project_dir)):
            return None
        venv_dir, _, exit_code = output

        # Hmm... "hatch" prints exception to stdout.
        # E.g., you run "hatch env find" in root `/` directory.
        if exit_code != 0 or not venv_dir:
            return None
        return VenvInfo.from_venv_dir(venv_dir)


class PdmVenvFinder(BaseVenvFinder):
    """
    Finds the virtual environment using `pdm`.

    @see https://github.com/pdm-project/pdm
    """

    @classmethod
    def _can_support(cls, project_dir: Path) -> bool:
        return bool(shutil.which("pdm") and (project_dir / ".pdm-python").is_file())

    def _find_venv(self) -> VenvInfo | None:
        if not (output := self._run_shell_command("pdm info --python", cwd=self.project_dir)):
            return None
        python_executable, _, _ = output

        if not python_executable:
            return None
        return VenvInfo.from_python_executable(python_executable)


class PipenvVenvFinder(BaseVenvFinder):
    """
    Finds the virtual environment using `pipenv`.

    @see https://github.com/python-poetry/poetry
    """

    @classmethod
    def _can_support(cls, project_dir: Path) -> bool:
        return bool(shutil.which("pipenv") and (project_dir / "Pipfile").is_file())

    def _find_venv(self) -> VenvInfo | None:
        if not (output := self._run_shell_command("pipenv --py", cwd=self.project_dir)):
            return None
        python_executable, _, _ = output

        if not python_executable:
            return None
        return VenvInfo.from_python_executable(python_executable)


class PoetryVenvFinder(BaseVenvFinder):
    """Finds the virtual environment using `poetry`."""

    @classmethod
    def _can_support(cls, project_dir: Path) -> bool:
        return bool(shutil.which("poetry") and (project_dir / "poetry.lock").is_file())

    def _find_venv(self) -> VenvInfo | None:
        if not (output := self._run_shell_command("poetry env info -p", cwd=self.project_dir)):
            return None
        venv_dir, _, _ = output

        if not venv_dir:
            return None
        return VenvInfo.from_venv_dir(venv_dir)


class PyenvVenvFinder(BaseVenvFinder):
    """
    Finds the virtual environment using `pyenv`.

    @see https://github.com/pyenv/pyenv
    """

    @classmethod
    def _can_support(cls, project_dir: Path) -> bool:
        return bool(shutil.which("pyenv") and (project_dir / ".python-version").is_file())

    def _find_venv(self) -> VenvInfo | None:
        if not (output := self._run_shell_command("pyenv which python", cwd=self.project_dir)):
            return None
        python_executable, _, _ = output

        if not python_executable:
            return None
        return VenvInfo.from_python_executable(python_executable)


class RyeVenvFinder(BaseVenvFinder):
    """
    Finds the virtual environment using `rye`.

    @see https://github.com/astral-sh/rye
    """

    @classmethod
    def _can_support(cls, project_dir: Path) -> bool:
        return bool(shutil.which("rye") and (project_dir / "pyproject.toml").is_file())

    def _find_venv(self) -> VenvInfo | None:
        if not (output := self._run_shell_command("rye show", cwd=self.project_dir)):
            return None
        stdout, _, _ = output

        for line in iterate_by_line(stdout):
            pre, sep, post = line.partition(":")
            if sep and pre == "venv":
                return VenvInfo.from_venv_dir(post.strip())
        return None
