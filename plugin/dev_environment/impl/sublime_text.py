from __future__ import annotations

import inspect
import os
import re
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generator, Tuple, TypeVar

import sublime
from LSP.plugin.core.collections import DottedDict
from LSP.plugin.core.constants import ST_VERSION
from more_itertools import first_true
from typing_extensions import TypeAlias

from ..interfaces import BaseDevEnvironmentHandler

T = TypeVar("T")

VERSION_TUPLE_2: TypeAlias = Tuple[int, int]
"""E.g., `(3, 8)` means Python 3.8."""


class BaseVersionedSublimeTextDevEnvironmentHandler(BaseDevEnvironmentHandler, ABC):
    python_version: VERSION_TUPLE_2 = (-1, -1)
    python_version_no_dot: str = ""

    @classmethod
    def name(cls) -> str:
        return f"sublime_text_{cls.python_version_no_dot}"

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool:
        """Check if this handler is available in the current ST version."""

    @classmethod
    def can_support(cls, dev_environment: str) -> bool:
        return super().can_support(dev_environment) and cls.is_available()

    def handle_(self, *, settings: DottedDict) -> None:
        self._inject_extra_paths(settings=settings, paths=self.find_package_dependency_dirs())

    def find_package_dependency_dirs(self) -> list[str]:
        dep_dirs = sys.path.copy()

        # replace paths for target Python version
        # @see https://github.com/sublimelsp/LSP-pyright/issues/28
        re_pattern = re.compile(r"(python)(3\.?[0-9]+)", flags=re.IGNORECASE)
        dep_dirs = [re_pattern.sub(Rf"\g<1>{self.python_version_no_dot}", dep_dir) for dep_dir in dep_dirs]

        # move the "Packages/" to the last
        # @see https://github.com/sublimelsp/LSP-pyright/pull/26#discussion_r520747708
        packages_path = sublime.packages_path()
        dep_dirs.remove(packages_path)
        dep_dirs.append(packages_path)

        # sublime stubs - add as first
        if self.python_version == (3, 3):
            dep_dirs.insert(0, str(self.server_dir / "resources/typings/sublime_text_py33"))

        return list(filter(os.path.isdir, dep_dirs))


class SublimeText33DevEnvironmentHandler(BaseVersionedSublimeTextDevEnvironmentHandler):
    """This handler will just assume the project uses Python 3.3."""

    python_version = (3, 3)
    python_version_no_dot = "33"

    @classmethod
    def is_available(cls) -> bool:
        return True


class SublimeText38DevEnvironmentHandler(BaseVersionedSublimeTextDevEnvironmentHandler):
    """This handler will just assume the project uses Python 3.8."""

    python_version = (3, 8)
    python_version_no_dot = "38"

    @classmethod
    def is_available(cls) -> bool:
        return 4200 >= ST_VERSION >= 4107


class SublimeText313DevEnvironmentHandler(BaseVersionedSublimeTextDevEnvironmentHandler):
    """This handler will just assume the project uses Python 3.13."""

    python_version = (3, 13)
    python_version_no_dot = "313"

    @classmethod
    def is_available(cls) -> bool:
        return ST_VERSION >= 4201


def list_all_subclasses(
    root: type[T],
    skip_abstract: bool = False,
    skip_self: bool = False,
) -> Generator[type[T], None, None]:
    """Gets all sub-classes of the root class."""
    if not skip_self and not (skip_abstract and inspect.isabstract(root)):
        yield root
    for leaf in root.__subclasses__():
        yield from list_all_subclasses(leaf, skip_self=False, skip_abstract=skip_abstract)


VERSIONED_SUBLIME_TEXT_DEV_ENVIRONMENT_HANDLERS = sorted(
    list_all_subclasses(BaseVersionedSublimeTextDevEnvironmentHandler, skip_abstract=True),  # type: ignore
    key=lambda cls: cls.python_version,
)
"""Collects all versioned ST dev environment handlers. Sorted by `python_version` ascending."""

AVAILABLE_ST_DEV_ENV_HANDLERS = [cls for cls in VERSIONED_SUBLIME_TEXT_DEV_ENVIRONMENT_HANDLERS if cls.is_available()]
LATEST_ST_DEV_ENV_HANDLER = AVAILABLE_ST_DEV_ENV_HANDLERS[-1]
OLDEST_ST_DEV_ENV_HANDLER = AVAILABLE_ST_DEV_ENV_HANDLERS[0]


class SublimeTextDevEnvironmentHandler(BaseDevEnvironmentHandler):
    """This handler uses the most appropriate handler based on the detected Sublime Text plugin Python version."""

    DOT_PYTHON_VERSION_RE = re.compile(rb"^(\d+)\.(\d+)", re.MULTILINE)

    @classmethod
    def name(cls) -> str:
        return "sublime_text"

    def handle_(self, *, settings: DottedDict) -> None:
        handler_cls = self.resolve_handler_cls(self.detect_project_python_version())
        handler = handler_cls(server_dir=self.server_dir, workspace_folders=self.workspace_folders)
        return handler.handle(settings=settings)

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
            AVAILABLE_ST_DEV_ENV_HANDLERS,
            pred=lambda cls: cls.python_version >= wanted_version,
            default=LATEST_ST_DEV_ENV_HANDLER,
        )
