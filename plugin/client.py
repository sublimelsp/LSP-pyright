from __future__ import annotations

import json
import os
import re
from typing import Any, cast

import jmespath
import sublime
import sublime_plugin
from LSP.plugin import DottedDict, MarkdownLangMap, Response
from LSP.plugin.core.protocol import CompletionItem, Hover, SignatureHelp
from lsp_utils import NpmClientHandler
from sublime_lib import ResourcePath

from .constants import PACKAGE_NAME, SERVER_SETTING_DEV_ENVIRONMENT
from .dev_environment.helpers import get_dev_environment_handler
from .log import log_error, log_warning
from .utils_lsp import AbstractLspPythonPlugin, find_workspace_folder, update_view_status_bar_text, uri_to_file_path
from .virtual_env.helpers import find_venv_by_finder_names


class ViewEventListener(sublime_plugin.ViewEventListener):
    def on_activated(self) -> None:
        settings = self.view.settings()

        if settings.get("lsp_active"):
            update_view_status_bar_text(LspPyrightPlugin, self.view)


class LspPyrightPlugin(AbstractLspPythonPlugin, NpmClientHandler):
    package_name = PACKAGE_NAME
    server_directory = "language-server"
    server_binary_path = os.path.join(server_directory, "node_modules", "pyright", "langserver.index.js")

    @classmethod
    def required_node_version(cls) -> str:
        """
        Testing playground at https://semver.npmjs.com
        And `0.0.0` means "no restrictions".
        """
        return ">=14.18.0"

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
                if dev_environment.startswith("sublime_text_") and handler.name() != dev_environment:
                    log_warning(
                        f'Development environment "{dev_environment}" is unsupported. '
                        f'Using "{handler.name()}" instead.',
                    )
                handler.handle(settings=settings)
        except Exception as ex:
            log_error(f'Failed to update extra paths for dev environment "{dev_environment}": {ex}')

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

    def on_workspace_configuration(self, params: Any, configuration: dict[str, Any]) -> dict[str, Any]:
        if not ((session := self.weaksession()) and (params.get("section") == "python")):
            return configuration

        scope_uri: str = params.get("scopeUri") or ""
        file_path = uri_to_file_path(scope_uri)
        wf_path = find_workspace_folder(session.window, file_path) if file_path else None

        # provide detected venv information
        # note that `pyrightconfig.json` seems to be auto-prioritized by the server
        if (
            # ...
            (venv_strategies := session.config.settings.get("venvStrategies"))
            and (venv_info := find_venv_by_finder_names(venv_strategies, project_dir=wf_path, session=session))
        ):
            if wf_path:
                self.wf_attrs[wf_path].venv_info = venv_info
            # When ST just starts, server session hasn't been created yet.
            # So `on_activated` can't add full information for the initial view and hence we handle it here.
            if active_view := sublime.active_window().active_view():
                update_view_status_bar_text(self.__class__, active_view)

            # modify configuration for the venv
            site_packages_dir = str(venv_info.site_packages_dir)
            conf_analysis: dict[str, Any] = configuration.setdefault("analysis", {})
            conf_analysis_extra_paths: list[str] = conf_analysis.setdefault("extraPaths", [])
            if site_packages_dir not in conf_analysis_extra_paths:
                conf_analysis_extra_paths.insert(0, site_packages_dir)
            if not configuration.get("pythonPath"):
                configuration["pythonPath"] = str(venv_info.python_executable)

        return configuration

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
