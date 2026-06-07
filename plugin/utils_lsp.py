"""Utility functions related to LSP."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import sublime
from LSP.plugin import parse_uri

from .utils import drop_falsy, resolved_posix_path
from .virtual_env.venv_info import BaseVenvInfo


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


class ConfigurationSection:
    def __init__(self, section: str | None) -> None:
        self.parts = section.split(".") if section else []

    def __contains__(self, other_section: ConfigurationSection) -> bool:
        return other_section.parts[: len(self.parts)] == self.parts

    def __str__(self) -> str:
        return f"ConfigurationSection({'.'.join(self.parts)})"


class ConfigurationProxy:
    """
    Holds full or part of the configuration and exposes access through absolute keys to that slice of configuration.

    The `section` defines which slice of the whole configuration is available for access. For example the available
    configuration might just expose the "python.analysis" sub-object of the whole configuraiton. The exposed get/set
    methods allow accessing that slice of the configuration using absolute key. For example
    get("python.analysis.extraPaths") returns value from within that configuration while get("python") returns `None`.
    """

    def __init__(self, configuration: dict[str, Any], section: ConfigurationSection) -> None:
        self.configuration = configuration
        self.section = section

    def get(self, key: str) -> Any:
        target_section = ConfigurationSection(key)
        if target_section not in self.section:
            return None
        # Path relative to the object we actually hold.
        relative_parts = target_section.parts[len(self.section.parts) :]
        if not relative_parts:
            return self.configuration
        node: Any = self.configuration
        for part in relative_parts[:-1]:
            if not isinstance(node, dict) or part not in node:
                return None
            node = node[part]
        last = relative_parts[-1]
        if not isinstance(node, dict) or last not in node:
            return None
        return node[last]

    def set(self, key: str, value: Any) -> None:
        target_section = ConfigurationSection(key)
        if target_section not in self.section:
            return
        # Path relative to the object we actually hold.
        relative_parts = target_section.parts[len(self.section.parts) :]
        if not relative_parts:
            return  # target == the section itself; can't set the root
        # Walk to the parent, creating missing intermediate dicts along the way.
        node: Any = self.configuration
        for part in relative_parts[:-1]:
            if not isinstance(node, dict):
                return
            node = node.setdefault(part, {})
        last: str = relative_parts[-1]
        if not isinstance(node, dict):
            return
        node[last] = value
