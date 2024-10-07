from __future__ import annotations

import contextlib
import os
import re
import sys
from abc import ABC
from pathlib import Path

import sublime
from LSP.plugin.core.collections import DottedDict

from ..interfaces import BaseDevEnvironmentHandler


class BaseSublimeTextDevEnvironmentHandler(BaseDevEnvironmentHandler, ABC):
    @property
    def python_version(self) -> tuple[int, int]:
        return (3, 3)

    def handle_(self, *, settings: DottedDict) -> None:
        self._inject_extra_paths(settings=settings, paths=self.find_package_dependency_dirs(), operation="replace")

    def find_package_dependency_dirs(self) -> list[str]:
        dep_dirs = sys.path.copy()

        # replace paths for target Python version
        # @see https://github.com/sublimelsp/LSP-pyright/issues/28
        re_pattern = re.compile(r"(python3\.?)[38]", flags=re.IGNORECASE)
        re_replacement = r"\g<1>8" if self.python_version == (3, 8) else r"\g<1>3"
        dep_dirs = [re_pattern.sub(re_replacement, dep_dir) for dep_dir in dep_dirs]

        # move the "Packages/" to the last
        # @see https://github.com/sublimelsp/LSP-pyright/pull/26#discussion_r520747708
        packages_path = sublime.packages_path()
        dep_dirs.remove(packages_path)
        dep_dirs.append(packages_path)

        # sublime stubs - add as first
        if self.python_version == (3, 3):
            dep_dirs.insert(0, str(self.server_dir / "resources/typings/sublime_text_py33"))

        return list(filter(os.path.isdir, dep_dirs))


class SublimeText33DevEnvironmentHandler(BaseSublimeTextDevEnvironmentHandler):
    @classmethod
    def name(cls) -> str:
        return "sublime_text_33"

    @property
    def python_version(self) -> tuple[int, int]:
        return (3, 3)


class SublimeText38DevEnvironmentHandler(BaseSublimeTextDevEnvironmentHandler):
    @classmethod
    def name(cls) -> str:
        return "sublime_text_38"

    @property
    def python_version(self) -> tuple[int, int]:
        return (3, 8)


class SublimeTextDevEnvironmentHandler(BaseSublimeTextDevEnvironmentHandler):
    def handle_(self, *, settings: DottedDict) -> None:
        handler_cls = self.resolve_handler_cls()
        handler = handler_cls(server_dir=self.server_dir, workspace_folders=self.workspace_folders)
        handler.handle(settings=settings)

    def resolve_handler_cls(self) -> type[BaseSublimeTextDevEnvironmentHandler]:
        py_ver = self.detect_st_py_ver()
        if py_ver == (3, 3):
            return SublimeText33DevEnvironmentHandler
        if py_ver == (3, 8):
            return SublimeText38DevEnvironmentHandler
        raise ValueError(f"Unsupported Python version: {py_ver}")

    def detect_st_py_ver(self) -> tuple[int, int]:
        def _is_py38() -> bool:
            try:
                first_folder = Path(self.workspace_folders[0]).resolve()
            except Exception:
                return False

            # ST auto uses py38 for files in "Packages/User/"
            if (Path(sublime.packages_path()) / "User") in (first_folder, *first_folder.parents):
                return True

            with contextlib.suppress(Exception):
                # the project wants to use py38
                if (first_folder / ".python-version").read_bytes().strip() == b"3.8":
                    return True

            return False

        return (3, 8) if _is_py38() else self.python_version
