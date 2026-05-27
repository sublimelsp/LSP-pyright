from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, final

import jmespath
import sublime
import sublime_plugin
from LSP.plugin import ClientResponse, LspPlugin, OnPreStartContext, ServerResponse
from lsp_utils import NodeManager
from sublime_lib import ResourcePath
from typing_extensions import override

from .constants import PACKAGE_NAME, SERVER_SETTING_DEV_ENVIRONMENT
from .dev_environment.helpers import get_dev_environment_handler
from .log import log_error, log_warning
from .utils_lsp import WorkspaceFolderAttr, find_workspace_folder, uri_to_file_path
from .virtual_env.helpers import find_venv_by_finder_names


class ViewEventListener(sublime_plugin.ViewEventListener):
    def on_activated(self) -> None:
        if (settings := self.view.settings()) and settings.get("lsp_active"):
            self.view.run_command("lsp_pyright_update_view_status_text")


@final
class LspPyrightPlugin(LspPlugin):
    server_version: str = ""
    """The version of the language server."""
    wf_attrs: defaultdict[Path, WorkspaceFolderAttr] = defaultdict(WorkspaceFolderAttr)
    """Per workspace folder attributes."""

    @classmethod
    def resolve_server_version(cls) -> None:
        lock_file_content = sublime.load_resource(f"Packages/{PACKAGE_NAME}/language-server/package-lock.json")
        cls.server_version = jmespath.search("dependencies.pyright.version", json.loads(lock_file_content)) or ""

    @classmethod
    @override
    def on_pre_start_async(cls, context: OnPreStartContext) -> None:
        package_name = cls.plugin_storage_path.name
        server_directory = NodeManager.on_pre_start_async(
            context,
            cls.plugin_storage_path,
            ResourcePath("Packages", package_name, "language-server"),
            Path("node_modules", "pyright", "langserver.index.js"),
            node_version_requirement=">=14.18.0",
        )
        if server_directory:
            overwrites_path = ResourcePath("Packages", package_name, "overwrites")
            try:
                overwrites_path.copytree(server_directory, exist_ok=True)
            except OSError:
                raise RuntimeError(f'Failed to copy overwrite dirs from "{overwrites_path}" to "{server_directory}".')

    @override
    def on_initialized_async(self) -> None:
        if not (session := self.weaksession()):
            return
        dev_environment = session.config.settings.get(SERVER_SETTING_DEV_ENVIRONMENT)
        try:
            if handler := get_dev_environment_handler(
                dev_environment,
                package_storage_path=self.plugin_storage_path,
                workspace_folders=tuple(map(str, session.get_workspace_folders())),
            ):
                if dev_environment.startswith("sublime_text_") and handler.name() != dev_environment:
                    log_warning(
                        f'Development environment "{dev_environment}" is unsupported. '
                        f'Using "{handler.name()}" instead.',
                    )
                handler.handle(config=session.config)
        except Exception as ex:
            log_error(f'Failed to update extra paths for dev environment "{dev_environment}": {ex}')

    @override
    def on_server_response_async(self, response: ServerResponse) -> None:
        if response["method"] == "textDocument/hover":
            if hover := response["result"]:
                contents = hover["contents"]
                if isinstance(contents, dict) and contents.get("kind") == "markdown":
                    contents["value"] = self.patch_markdown_content(contents["value"])
            return
        if response["method"] == "completionItem/resolve":
            completion = response["result"]
            documentation = completion.get("documentation")
            if isinstance(documentation, dict) and documentation.get("kind") == "markdown":
                documentation["value"] = self.patch_markdown_content(documentation["value"])
            return
        if response["method"] == "textDocument/signatureHelp":
            if signature_help := response["result"]:
                for signature in signature_help["signatures"]:
                    documentation = signature.get("documentation")
                    if isinstance(documentation, dict) and documentation.get("kind") == "markdown":
                        documentation["value"] = self.patch_markdown_content(documentation["value"])
                    for parameter in signature.get("parameters") or []:
                        documentation = parameter.get("documentation")
                        if isinstance(documentation, dict) and documentation.get("kind") == "markdown":
                            documentation["value"] = self.patch_markdown_content(documentation["value"])
            return

    @override
    def on_pre_send_response_async(self, response: ClientResponse) -> None:
        if response["method"] == "workspace/configuration" and (session := self.weaksession()):
            for i, item in enumerate(response["params"]["items"]):
                if item.get("section") == "python":
                    continue
                configuration = response["result"][i]
                if not isinstance(configuration, dict):
                    continue
                scope_uri = item.get("scopeUri", "")
                file_path = uri_to_file_path(scope_uri)
                wf_path = find_workspace_folder(session.window, file_path) if file_path else None
                # provide detected venv information
                # note that `pyrightconfig.json` seems to be auto-prioritized by the server
                if (venv_strategies := session.config.settings.get("venvStrategies")) and (
                    venv_info := find_venv_by_finder_names(venv_strategies, project_dir=wf_path, session=session)
                ):
                    if wf_path:
                        self.wf_attrs[wf_path].venv_info = venv_info
                    # When ST just starts, server session hasn't been created yet.
                    # So `on_activated` can't add full information for the initial view and hence we handle it here.
                    if active_view := sublime.active_window().active_view():
                        active_view.run_command("lsp_pyright_update_view_status_text")

                    # modify configuration for the venv
                    site_packages_dir = str(venv_info.site_packages_dir)
                    conf_analysis: dict[str, Any] = configuration.setdefault("analysis", {})
                    conf_analysis_extra_paths: list[str] = conf_analysis.setdefault("extraPaths", [])
                    if site_packages_dir not in conf_analysis_extra_paths:
                        conf_analysis_extra_paths.insert(0, site_packages_dir)
                    if not configuration.get("pythonPath"):
                        configuration["pythonPath"] = str(venv_info.python_executable)

    def patch_markdown_content(self, content: str) -> str:
        # the fenced code blocks are not valid Python hence we use a custom syntax
        content = re.sub("```python(?=\n)", "```pyright_python", content)
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
