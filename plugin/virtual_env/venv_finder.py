from __future__ import annotations

import os
import shutil
from abc import ABC, abstractmethod
from functools import lru_cache
from itertools import product
from pathlib import Path
from types import MappingProxyType
from typing import Generator, Mapping, final

from more_itertools import first_true

from ..utils import camel_to_snake, iterate_by_line, remove_suffix, run_shell_command
from .venv_info import BaseVenvInfo, CondaVenvInfo, Pep405VenvInfo, list_venv_info_classes


@lru_cache
def find_finder_class_by_name(name: str) -> type[BaseVenvFinder] | None:
    """Finds the virtual environment finder class by its name."""
    return get_finder_name_mapping().get(name)


@lru_cache
def get_finder_name_mapping() -> Mapping[str, type[BaseVenvFinder]]:
    """Returns a mapping of virtual environment finder names to their classes."""
    return MappingProxyType({finder_cls.name(): finder_cls for finder_cls in list_venv_finder_classes()})


def list_venv_finder_classes() -> Generator[type[BaseVenvFinder], None, None]:
    """
    Lists all virtual environment finder classes.

    The order matters because they will be used for testing one by one.
    """
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


class BaseVenvFinder(ABC):
    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir
        """The project root directory."""

    @final
    @classmethod
    def name(cls) -> str:
        return camel_to_snake(remove_suffix(cls.__name__, "VenvFinder"))

    @classmethod
    @abstractmethod
    def can_support(cls, project_dir: Path) -> bool:
        """Check if this class support the given `project_dir`."""

    @final
    def find_venv(self) -> BaseVenvInfo | None:
        """Find the virtual environment."""
        try:
            if not (venv_info := self.find_venv_()):
                return None
        except PermissionError:
            return None

        venv_info.meta.finder_name = self.name()
        return venv_info

    @abstractmethod
    def find_venv_(self) -> BaseVenvInfo | None:
        """Find the virtual environment. Implement this method by the subclass."""


class AnySubdirectoryVenvFinder(BaseVenvFinder):
    """Finds the virtual environment with any subdirectory."""

    @classmethod
    def can_support(cls, project_dir: Path) -> bool:
        return True

    def find_venv_(self) -> BaseVenvInfo | None:
        for subproject_dir, venv_info_cls in product(self.project_dir.iterdir(), list_venv_info_classes()):
            if venv_info := venv_info_cls.from_venv_dir(subproject_dir):
                return venv_info
        return None


class EnvVarCondaPrefixVenvFinder(BaseVenvFinder):
    """
    Finds the virtual environment using the `CONDA_PREFIX` environment variable.

    @see https://github.com/conda/conda
    """

    @classmethod
    def can_support(cls, project_dir: Path) -> bool:
        return "CONDA_PREFIX" in os.environ

    def find_venv_(self) -> CondaVenvInfo | None:
        return CondaVenvInfo.from_venv_dir(os.environ["CONDA_PREFIX"])


class EnvVarVirtualEnvVenvFinder(BaseVenvFinder):
    """
    Finds the virtual environment using the `VIRTUAL_ENV` environment variable.

    @see https://docs.python.org/library/venv.html
    """

    @classmethod
    def can_support(cls, project_dir: Path) -> bool:
        return "VIRTUAL_ENV" in os.environ

    def find_venv_(self) -> Pep405VenvInfo | None:
        return Pep405VenvInfo.from_venv_dir(os.environ["VIRTUAL_ENV"])


class LocalDotVenvVenvFinder(BaseVenvFinder):
    """
    Finds the virtual environment `.venv` or `venv` directory.

    @see https://docs.python.org/library/venv.html
    """

    @classmethod
    def can_support(cls, project_dir: Path) -> bool:
        return True

    def find_venv_(self) -> Pep405VenvInfo | None:
        return first_true(
            map(
                Pep405VenvInfo.from_venv_dir,
                (self.project_dir / ".venv", self.project_dir / "venv"),
            )
        )


class HatchVenvFinder(BaseVenvFinder):
    """
    Finds the virtual environment using `hatch`.

    @see https://github.com/pypa/hatch
    """

    @classmethod
    def can_support(cls, project_dir: Path) -> bool:
        return bool(shutil.which("hatch"))

    def find_venv_(self) -> Pep405VenvInfo | None:
        # "hatch env find" will always provide a calculated path, where the hatch-managed venv should be at
        if not (output := run_shell_command("hatch env find", cwd=self.project_dir)):
            return None
        venv_dir, _, exit_code = output

        # Hmm... "hatch" prints exception to stdout.
        # E.g., you run "hatch env find" in root `/` directory.
        if exit_code != 0 or not venv_dir:
            return None
        return Pep405VenvInfo.from_venv_dir(venv_dir)


class PdmVenvFinder(BaseVenvFinder):
    """
    Finds the virtual environment using `pdm`.

    @see https://github.com/pdm-project/pdm
    """

    @classmethod
    def can_support(cls, project_dir: Path) -> bool:
        try:
            return bool(shutil.which("pdm") and (project_dir / ".pdm-python").is_file())
        except Exception:
            return False

    def find_venv_(self) -> Pep405VenvInfo | None:
        if not (output := run_shell_command("pdm info --python", cwd=self.project_dir)):
            return None
        python_executable, _, _ = output

        if not python_executable:
            return None
        return Pep405VenvInfo.from_python_executable(python_executable)


class PipenvVenvFinder(BaseVenvFinder):
    """
    Finds the virtual environment using `pipenv`.

    @see https://github.com/python-poetry/poetry
    """

    @classmethod
    def can_support(cls, project_dir: Path) -> bool:
        try:
            return bool(shutil.which("pipenv") and (project_dir / "Pipfile").is_file())
        except Exception:
            return False

    def find_venv_(self) -> Pep405VenvInfo | None:
        if not (output := run_shell_command("pipenv --py", cwd=self.project_dir)):
            return None
        python_executable, _, _ = output

        if not python_executable:
            return None
        return Pep405VenvInfo.from_python_executable(python_executable)


class PoetryVenvFinder(BaseVenvFinder):
    """Finds the virtual environment using `poetry`."""

    @classmethod
    def can_support(cls, project_dir: Path) -> bool:
        try:
            return bool(shutil.which("poetry") and (project_dir / "poetry.lock").is_file())
        except Exception:
            return False

    def find_venv_(self) -> Pep405VenvInfo | None:
        if not (output := run_shell_command("poetry env info -p", cwd=self.project_dir)):
            return None
        venv_dir, _, _ = output

        if not venv_dir:
            return None
        return Pep405VenvInfo.from_venv_dir(venv_dir)


class PyenvVenvFinder(BaseVenvFinder):
    """
    Finds the virtual environment using `pyenv`.

    @see https://github.com/pyenv/pyenv
    """

    @classmethod
    def can_support(cls, project_dir: Path) -> bool:
        try:
            return bool(shutil.which("pyenv") and (project_dir / ".python-version").is_file())
        except Exception:
            return False

    def find_venv_(self) -> Pep405VenvInfo | None:
        if not (output := run_shell_command("pyenv which python", cwd=self.project_dir)):
            return None
        python_executable, _, _ = output

        if not python_executable:
            return None
        return Pep405VenvInfo.from_python_executable(python_executable)


class RyeVenvFinder(BaseVenvFinder):
    """
    Finds the virtual environment using `rye`.

    @see https://github.com/astral-sh/rye
    """

    @classmethod
    def can_support(cls, project_dir: Path) -> bool:
        try:
            return bool(shutil.which("rye") and (project_dir / "pyproject.toml").is_file())
        except Exception:
            return False

    def find_venv_(self) -> Pep405VenvInfo | None:
        if not (output := run_shell_command("rye show", cwd=self.project_dir)):
            return None
        stdout, _, _ = output

        for line in iterate_by_line(stdout):
            pre, sep, post = line.partition(":")
            if sep and pre == "venv":
                return Pep405VenvInfo.from_venv_dir(post.strip())
        return None
