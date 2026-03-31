"""Utility functions related to LSP."""

from __future__ import annotations

from .utils import drop_falsy
from .utils import resolved_posix_path
from .virtual_env.venv_info import BaseVenvInfo
from dataclasses import dataclass
from LSP.plugin import parse_uri
from pathlib import Path
import sublime


@dataclass
class WorkspaceFolderAttr:
    venv_info: BaseVenvInfo | None = None
    """The information of the virtual environment."""


def find_workspace_folder(window: sublime.Window, path: str | Path) -> Path | None:
    """Find a workspace folder for the path. The deepest folder wins if there are multiple matches."""
    if path_ := resolved_posix_path(path):
        for folder in sorted(drop_falsy(map(resolved_posix_path, window.folders())), key=len, reverse=True):
            if f"{path_}/".startswith(f"{folder}/"):
                return Path(folder)
    return None


def lowercase_drive_letter(path: str) -> str:
    """Converts the drive letter in the path to lowercase."""
    if len(path) > 1 and path[1] == ":":
        return path[0].lower() + path[1:]
    return path


def uri_to_file_path(uri: str) -> str | None:
    """Converts the URI to its file path if it's of the "file" scheme. Otherwise, `None`."""
    scheme, path = parse_uri(uri)
    return path if scheme == "file" else None
