"""Utility functions related to LSP."""

from __future__ import annotations

from abc import ABC
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import sublime
from LSP.plugin import AbstractPlugin as AbstractLspPlugin
from LSP.plugin import parse_uri
from LSP.plugin.core.registry import windows as lsp_windows_registry

from .log import log_warning
from .template import load_string_template
from .utils import drop_falsy, resolved_posix_path
from .virtual_env.venv_finder import BaseVenvInfo


@dataclass
class WorkspaceFolderAttr:
    venv_info: BaseVenvInfo | None = None
    """The information of the virtual environment."""


class AbstractLspPythonPlugin(AbstractLspPlugin, ABC):
    server_version: str = ""
    """The version of the language server."""
    wf_attrs: defaultdict[Path, WorkspaceFolderAttr] = defaultdict(WorkspaceFolderAttr)
    """Per workspace folder attributes."""


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


def update_view_status_bar_text(
    lsp_cls: type[AbstractLspPythonPlugin],
    view: sublime.View,
    *,
    extra_variables: dict[str, Any] | None = None,
) -> None:
    if not (
        (file_path := view.file_name())
        and (window := view.window())
        and (lsp_window_manager := lsp_windows_registry.lookup(window))
        and (session := lsp_window_manager.get_session(lsp_cls.name(), file_path))
    ):
        return

    # shortcut if the user doesn't want any status text
    if not (template_text := str(session.config.settings.get("statusText") or "")):
        session.set_config_status_async("")
        return

    variables: dict[str, Any] = {
        "server_version": lsp_cls.server_version,
    }

    if (
        (wf_path := find_workspace_folder(window, file_path))
        and (wf_attr := lsp_cls.wf_attrs.get(wf_path))
        and (venv_info := wf_attr.venv_info)
    ):
        variables["venv"] = {
            "finder_name": venv_info.meta.finder_name,
            "python_version": venv_info.python_version,
            "venv_prompt": venv_info.prompt,
        }

    if extra_variables:
        variables.update(extra_variables)

    rendered_text = ""
    try:
        rendered_text = load_string_template(template_text).render(variables)
    except Exception as e:
        log_warning(f'Invalid "statusText" template: {e}')

    session.set_config_status_async(rendered_text)
