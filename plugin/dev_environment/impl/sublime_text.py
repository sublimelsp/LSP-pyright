from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Tuple

import sublime
from LSP.plugin import DottedDict
from lsp_utils import UvVenvManager
from more_itertools import first_true
from sublime_lib import ResourcePath
from typing_extensions import TypeAlias, override

from ...constants import PACKAGE_NAME
from ..interfaces import BaseDevEnvironmentHandler

VERSION_TUPLE_2: TypeAlias = Tuple[int, int]
"""E.g., `(3, 8)` means Python 3.8."""


class BaseVersionedSublimeTextDevEnvironmentHandler(BaseDevEnvironmentHandler):
    python_version: VERSION_TUPLE_2 = (-1, -1)
    python_version_no_dot: str = ""

    @classmethod
    def name(cls) -> str:
        return f"sublime_text_{cls.python_version_no_dot}"

    @classmethod
    def can_support(cls, dev_environment: str) -> bool:
        if not dev_environment.startswith("sublime_text_"):
            return False
        wanted_version_no_dot = dev_environment.rpartition("_")[2]
        wanted_version = (int(wanted_version_no_dot[0]), int(wanted_version_no_dot[1:]))
        return cls.python_version >= wanted_version

    @classmethod
    def stubs_venv_manager(cls, package_storage_path: Path) -> UvVenvManager:
        """Manages the venv with the Sublime Text API stubs for this Python version (`resources/sublime_text_pyXY`)."""
        return UvVenvManager(
            package_storage_path,
            ResourcePath("Packages", PACKAGE_NAME, "resources", f"sublime_text_py{cls.python_version_no_dot}"),
        )

    @override
    def install_async(self) -> None:
        """Installs the Sublime Text API stubs for this Python version. Blocks while installing."""
        self.stubs_venv_manager(self.package_storage_path).install_async()

    def find_stubs_dir(self) -> Path | None:
        """The `site-packages` dir of the stubs venv, which contains the `*-stubs` packages."""
        venv_path = self.stubs_venv_manager(self.package_storage_path).venv_path
        return first_true(
            (*venv_path.glob("lib/python*/site-packages"), venv_path / "Lib" / "site-packages"),
            pred=Path.is_dir,
        )

    @override
    def resolve_extra_paths_(self, *, settings: DottedDict) -> list[str]:
        return self._resolve_paths(settings=settings, paths=self.find_package_dependency_dirs())

    def find_package_dependency_dirs(self) -> list[str]:
        dep_dirs = sys.path.copy()

        # replace paths for target Python version
        # @see https://github.com/sublimelsp/LSP-pyright/issues/28
        re_pattern = re.compile(r"(python)(3\.?[0-9]+)", flags=re.IGNORECASE)
        dep_dirs = [re_pattern.sub(Rf"\g<1>{self.python_version_no_dot}", dep_dir) for dep_dir in dep_dirs]

        # Expose unittesting module.
        dep_dirs.append(os.path.join(sublime.packages_path(), "UnitTesting"))

        # move the "Packages/" to the last
        # @see https://github.com/sublimelsp/LSP-pyright/pull/26#discussion_r520747708
        packages_path = sublime.packages_path()
        dep_dirs.remove(packages_path)
        dep_dirs.append(packages_path)

        # Sublime Text API stubs - add as first so that they take precedence over the API modules
        # (`sublime.py`, `sublime_plugin.py`) of the running Sublime Text, which are found in `sys.path`.
        if stubs_dir := self.find_stubs_dir():
            dep_dirs.insert(0, str(stubs_dir))

        return list(filter(os.path.isdir, dep_dirs))


class SublimeText38DevEnvironmentHandler(BaseVersionedSublimeTextDevEnvironmentHandler):
    """This handler will just assume the project uses Python 3.8."""

    python_version = (3, 8)
    python_version_no_dot = "38"


class SublimeText314DevEnvironmentHandler(BaseVersionedSublimeTextDevEnvironmentHandler):
    """This handler will just assume the project uses Python 3.14."""

    python_version = (3, 14)
    python_version_no_dot = "314"


VERSIONED_SUBLIME_TEXT_DEV_ENVIRONMENT_HANDLERS: list[type[BaseVersionedSublimeTextDevEnvironmentHandler]] = [
    SublimeText38DevEnvironmentHandler,
    SublimeText314DevEnvironmentHandler,
]
"""All versioned ST dev environment handlers. Must be sorted by `python_version` ascending."""


LATEST_ST_DEV_ENV_HANDLER = VERSIONED_SUBLIME_TEXT_DEV_ENVIRONMENT_HANDLERS[-1]
OLDEST_ST_DEV_ENV_HANDLER = VERSIONED_SUBLIME_TEXT_DEV_ENVIRONMENT_HANDLERS[0]


class SublimeTextDevEnvironmentHandler(BaseDevEnvironmentHandler):
    """This handler uses the most appropriate handler based on the detected Sublime Text plugin Python version."""

    DOT_PYTHON_VERSION_RE = re.compile(rb"^(\d+)\.(\d+)", re.MULTILINE)

    @classmethod
    def name(cls) -> str:
        return "sublime_text"

    @override
    def install_async(self) -> None:
        self.resolve_handler().install_async()

    @override
    def resolve_extra_paths_(self, *, settings: DottedDict) -> list[str]:
        return self.resolve_handler().resolve_extra_paths(settings=settings)

    def resolve_handler(self) -> BaseVersionedSublimeTextDevEnvironmentHandler:
        handler_cls = self.resolve_handler_cls(self.detect_project_python_version())
        return handler_cls(package_storage_path=self.package_storage_path, workspace_folders=self.workspace_folders)

    def detect_project_python_version(self) -> VERSION_TUPLE_2:
        try:
            project_dir = Path(self.workspace_folders[0]).resolve()
        except Exception:
            return OLDEST_ST_DEV_ENV_HANDLER.python_version

        # ST auto uses the latest Python for files in "Packages/User/"
        if (Path(sublime.packages_path()) / "User") in (project_dir, *project_dir.parents):
            return LATEST_ST_DEV_ENV_HANDLER.python_version

        # detect from project's ".python-version" file
        if (py_version_file := (project_dir / ".python-version")).is_file() and (
            m := self.DOT_PYTHON_VERSION_RE.match(py_version_file.read_bytes())
        ):
            return (int(m[1]), int(m[2]))

        return OLDEST_ST_DEV_ENV_HANDLER.python_version

    @staticmethod
    def resolve_handler_cls(wanted_version: VERSION_TUPLE_2) -> type[BaseVersionedSublimeTextDevEnvironmentHandler]:
        """Returns the best matching handler class for the wanted Python version."""
        return first_true(
            VERSIONED_SUBLIME_TEXT_DEV_ENVIRONMENT_HANDLERS,
            pred=lambda cls: cls.python_version >= wanted_version,
            default=LATEST_ST_DEV_ENV_HANDLER,
        )
