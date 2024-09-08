from __future__ import annotations

import json
import os
import re
import shutil
import weakref
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import jmespath
import sublime
from LSP.plugin import ClientConfig, DottedDict, MarkdownLangMap, Response, WorkspaceFolder
from LSP.plugin.core.protocol import CompletionItem, Hover, SignatureHelp
from lsp_utils import NpmClientHandler
from more_itertools import first_true
from sublime_lib import ResourcePath

from .constants import PACKAGE_NAME, SERVER_SETTING_DEV_ENVIRONMENT
from .dev_environment.helpers import get_dev_environment_handler
from .log import log_error, log_info, log_warning
from .template import load_string_template
from .virtual_env.helpers import find_venv_by_finder_names, find_venv_by_python_executable
from .virtual_env.venv_finder import BaseVenvInfo, get_finder_name_mapping


@dataclass
class WindowAttr:
    simple_python_executable: Path | None = None
    """The path to the Python executable found by the `PATH` env variable."""
    venv_info: BaseVenvInfo | None = None
    """The information of the virtual environment."""

    @property
    def preferred_python_executable(self) -> Path | None:
        return self.venv_info.python_executable if self.venv_info else self.simple_python_executable


class LspPyrightPlugin(NpmClientHandler):
    package_name = PACKAGE_NAME
    server_directory = "language-server"
    server_binary_path = os.path.join(server_directory, "node_modules", "pyright", "langserver.index.js")

    server_version = ""
    """The version of the language server."""

    window_attrs: weakref.WeakKeyDictionary[sublime.Window, WindowAttr] = weakref.WeakKeyDictionary()
    """Per-window attributes. I.e., per-session attributes."""

    @classmethod
    def required_node_version(cls) -> str:
        """
        Testing playground at https://semver.npmjs.com
        And `0.0.0` means "no restrictions".
        """
        return ">=14"

    @classmethod
    def should_ignore(cls, view: sublime.View) -> bool:
        return bool(
            # SublimeREPL views
            view.settings().get("repl")
            # syntax test files
            or os.path.basename(view.file_name() or "").startswith("syntax_test")
        )

    @classmethod
    def setup(cls) -> None:
        super().setup()

        cls.server_version = cls.parse_server_version()

    @classmethod
    def can_start(
        cls,
        window: sublime.Window,
        initiating_view: sublime.View,
        workspace_folders: list[WorkspaceFolder],
        configuration: ClientConfig,
    ) -> str | None:
        if message := super().can_start(window, initiating_view, workspace_folders, configuration):
            return message

        cls.window_attrs.setdefault(window, WindowAttr())
        return None

    def on_settings_changed(self, settings: DottedDict) -> None:
        super().on_settings_changed(settings)

        if not ((session := self.weaksession()) and (server_dir := self._server_directory_path())):
            return

        dev_environment = settings.get(SERVER_SETTING_DEV_ENVIRONMENT) or ""
        try:
            if handler := get_dev_environment_handler(
                dev_environment,
                server_dir=server_dir,
                workspace_folders=tuple(map(str, session.get_workspace_folders())),
            ):
                handler.handle(settings=settings)
        except Exception as ex:
            log_error(f'Failed to update extra paths for dev environment "{dev_environment}": {ex}')

        self.update_status_bar_text()

    @classmethod
    def on_pre_start(
        cls,
        window: sublime.Window,
        initiating_view: sublime.View,
        workspace_folders: list[WorkspaceFolder],
        configuration: ClientConfig,
    ) -> str | None:
        super().on_pre_start(window, initiating_view, workspace_folders, configuration)

        cls.update_venv_info(configuration.settings, workspace_folders, window=window)
        if venv_info := cls.window_attrs[window].venv_info:
            log_info(f"Using python executable: {venv_info.python_executable}")
            configuration.settings.set("python.pythonPath", str(venv_info.python_executable))
        return None

    @classmethod
    def install_or_update(cls) -> None:
        super().install_or_update()
        cls.copy_overwrite_dirs()

    @classmethod
    def markdown_language_id_to_st_syntax_map(cls) -> MarkdownLangMap | None:
        return {"python": (("python", "py"), ("LSP-pyright/syntaxes/pyright",))}

    def on_server_response_async(self, method: str, response: Response) -> None:
        if method == "textDocument/hover" and isinstance(response.result, dict):
            hover = cast(Hover, response.result)
            contents = hover.get("contents")
            if isinstance(contents, dict) and contents.get("kind") == "markdown":
                contents["value"] = self.patch_markdown_content(contents["value"])
            return
        if method == "completionItem/resolve" and isinstance(response.result, dict):
            completion = cast(CompletionItem, response.result)
            documentation = completion.get("documentation")
            if isinstance(documentation, dict) and documentation.get("kind") == "markdown":
                documentation["value"] = self.patch_markdown_content(documentation["value"])
            return
        if method == "textDocument/signatureHelp" and isinstance(response.result, dict):
            signature_help = cast(SignatureHelp, response.result)
            for signature in signature_help["signatures"]:
                documentation = signature.get("documentation")
                if isinstance(documentation, dict) and documentation.get("kind") == "markdown":
                    documentation["value"] = self.patch_markdown_content(documentation["value"])
                for parameter in signature.get("parameters") or []:
                    documentation = parameter.get("documentation")
                    if isinstance(documentation, dict) and documentation.get("kind") == "markdown":
                        documentation["value"] = self.patch_markdown_content(documentation["value"])
            return

    # -------------- #
    # custom methods #
    # -------------- #

    @classmethod
    def copy_overwrite_dirs(cls) -> None:
        if not (server_dir := cls._server_directory_path()):
            log_warning("Failed to get the server instance during copying overwrite dirs.")
            return

        dir_src = f"Packages/{cls.package_name}/overwrites/"
        dir_dst = server_dir
        try:
            ResourcePath(dir_src).copytree(dir_dst, exist_ok=True)
        except OSError:
            raise RuntimeError(f'Failed to copy overwrite dirs from "{dir_src}" to "{dir_dst}".')

    def update_status_bar_text(self, extra_variables: dict[str, Any] | None = None) -> None:
        if not (session := self.weaksession()):
            return

        variables: dict[str, Any] = {
            "server_version": self.server_version,
        }

        if venv_info := self.window_attrs[session.window].venv_info:
            variables["venv"] = {
                "finder_name": venv_info.meta.finder_name,
                "python_version": venv_info.python_version,
                "venv_prompt": venv_info.prompt,
            }

        if extra_variables:
            variables.update(extra_variables)

        rendered_text = ""
        if template_text := str(session.config.settings.get("statusText") or ""):
            try:
                rendered_text = load_string_template(template_text).render(variables)
            except Exception as e:
                log_warning(f'Invalid "statusText" template: {e}')
        session.set_config_status_async(rendered_text)

    def patch_markdown_content(self, content: str) -> str:
        # add another linebreak before horizontal rule following fenced code block
        content = re.sub("```\n---", "```\n\n---", content)
        # add markup for some common field name conventions in function docstring
        content = re.sub(
            r"\n:(\w+)[ \t]+([\w\\*.]+):",
            lambda m: "\n__{field}:__ `{name}`".format(
                field=m.group(1).title(),
                name=m.group(2).replace(R"\_", "_").replace(R"\*", "*"),
            ),
            content,
        )
        content = re.sub(r"\n:returns?:", r"\n__Returns:__", content)
        content = re.sub(r"\n:rtype:", r"\n__Returntype:__", content)
        content = re.sub(r"\n:deprecated:", r"\n⚠️ __Deprecated:__", content)
        return content

    @classmethod
    def parse_server_version(cls) -> str:
        lock_file_content = sublime.load_resource(f"Packages/{PACKAGE_NAME}/language-server/package-lock.json")
        return jmespath.search("dependencies.pyright.version", json.loads(lock_file_content)) or ""

    @classmethod
    def update_venv_info(
        cls,
        settings: DottedDict,
        workspace_folders: list[WorkspaceFolder],
        *,
        window: sublime.Window,
    ) -> None:
        window_attr = cls.window_attrs[window]

        def _update_simple_python_path() -> None:
            window_attr.simple_python_executable = None

            if python_path := first_true(("py", "python3", "python"), pred=shutil.which):
                window_attr.simple_python_executable = Path(python_path)

        def _update_venv_info() -> None:
            window_attr.venv_info = None

            if python_path := settings.get("python.pythonPath"):
                window_attr.venv_info = find_venv_by_python_executable(python_path)
                return

            supported_finder_names = tuple(get_finder_name_mapping().keys())
            finder_names: list[str] = settings.get("venvStrategies")
            if invalid_finder_names := sorted(set(finder_names) - set(supported_finder_names)):
                log_warning(f"The following finder names are not supported: {', '.join(invalid_finder_names)}")

            if workspace_folders and (first_folder := Path(workspace_folders[0].path).resolve()):
                for folder in (first_folder, *first_folder.parents):
                    if venv_info := find_venv_by_finder_names(finder_names, project_dir=folder):
                        window_attr.venv_info = venv_info
                        return

        _update_simple_python_path()
        _update_venv_info()
