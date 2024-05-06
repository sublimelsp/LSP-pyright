from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import sublime
from LSP.plugin import ClientConfig, DottedDict, MarkdownLangMap, Response, WorkspaceFolder
from LSP.plugin.core.protocol import CompletionItem, Hover, SignatureHelp
from lsp_utils import NpmClientHandler
from sublime_lib import ResourcePath

assert __package__


def plugin_loaded() -> None:
    LspPyrightPlugin.setup()


def plugin_unloaded() -> None:
    LspPyrightPlugin.cleanup()


def get_default_startupinfo() -> Any:
    if sublime.platform() == "windows":
        # do not create a window for the process
        STARTUPINFO = subprocess.STARTUPINFO()  # type: ignore
        STARTUPINFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # type: ignore
        STARTUPINFO.wShowWindow = subprocess.SW_HIDE  # type: ignore
        return STARTUPINFO
    return None


class LspPyrightPlugin(NpmClientHandler):
    package_name = __package__.partition(".")[0]
    server_directory = "language-server"
    server_binary_path = os.path.join(server_directory, "node_modules", "pyright", "langserver.index.js")

    @classmethod
    def required_node_version(cls) -> str:
        """
        Testing playground at https://semver.npmjs.com
        And `0.0.0` means "no restrictions".
        """
        return ">=14"

    def on_settings_changed(self, settings: DottedDict) -> None:
        super().on_settings_changed(settings)

        dev_environment = settings.get("pyright.dev_environment")
        extraPaths: list[str] = settings.get("python.analysis.extraPaths") or []

        if dev_environment in {"sublime_text", "sublime_text_33", "sublime_text_38"}:
            py_ver = self.detect_st_py_ver(dev_environment)
            # add package dependencies into "python.analysis.extraPaths"
            extraPaths.extend(self.find_package_dependency_dirs(py_ver))

        settings.set("python.analysis.extraPaths", extraPaths)

    @classmethod
    def on_pre_start(
        cls,
        window: sublime.Window,
        initiating_view: sublime.View,
        workspace_folders: list[WorkspaceFolder],
        configuration: ClientConfig,
    ) -> str | None:
        super().on_pre_start(window, initiating_view, workspace_folders, configuration)

        python_path = cls.python_path(configuration.settings, workspace_folders)
        print(f'{cls.name()}: INFO: Using python path "{python_path}"')
        configuration.settings.set("python.pythonPath", python_path)
        return None

    @classmethod
    def install_or_update(cls) -> None:
        super().install_or_update()
        # Copy resources
        src = f"Packages/{cls.package_name}/resources/"
        dest = os.path.join(cls.package_storage(), "resources")
        ResourcePath(src).copytree(dest, exist_ok=True)

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

    def detect_st_py_ver(self, dev_environment: str) -> tuple[int, int]:
        default = (3, 3)

        if dev_environment == "sublime_text_33":
            return (3, 3)
        if dev_environment == "sublime_text_38":
            return (3, 8)
        if dev_environment == "sublime_text":
            if not ((session := self.weaksession()) and (workspace_folders := session.get_workspace_folders())):
                return default
            # ST auto uses py38 for files in "Packages/User/"
            if (first_folder := Path(workspace_folders[0].path).resolve()) == Path(sublime.packages_path()) / "User":
                return (3, 8)
            # the project wants to use py38
            try:
                if (first_folder / ".python-version").read_bytes().strip() == b"3.8":
                    return (3, 8)
            except Exception:
                pass
            return default

        raise ValueError(f'Invalid "dev_environment" setting: {dev_environment}')

    def find_package_dependency_dirs(self, py_ver: tuple[int, int] = (3, 3)) -> list[str]:
        dep_dirs = sys.path.copy()

        # replace paths for target Python version
        # @see https://github.com/sublimelsp/LSP-pyright/issues/28
        re_pattern = re.compile(r"(python3\.?)[38]", flags=re.IGNORECASE)
        re_replacement = r"\g<1>8" if py_ver == (3, 8) else r"\g<1>3"
        dep_dirs = [re_pattern.sub(re_replacement, dep_dir) for dep_dir in dep_dirs]

        # move the "Packages/" to the last
        # @see https://github.com/sublimelsp/LSP-pyright/pull/26#discussion_r520747708
        packages_path = sublime.packages_path()
        dep_dirs.remove(packages_path)
        dep_dirs.append(packages_path)

        # sublime stubs - add as first
        if py_ver == (3, 3):
            dep_dirs.insert(0, os.path.join(self.package_storage(), "resources", "typings", "sublime_text"))

        return list(filter(os.path.isdir, dep_dirs))

    @classmethod
    def python_path(cls, settings: DottedDict, workspace_folders: list[WorkspaceFolder]) -> str:
        if python_path := settings.get("python.pythonPath"):
            return python_path

        if workspace_folders:
            workspace_folder = Path(workspace_folders[0].path).resolve()
            for folder in (workspace_folder, *workspace_folder.parents):
                if python_path := cls.python_path_from_venv(folder):
                    return str(python_path)

        return shutil.which("python") or shutil.which("python3") or ""

    @classmethod
    def python_path_from_venv(cls, workspace_folder: str | Path) -> Path | None:
        """
        Resolves the python binary path depending on environment variables and files in the workspace.

        @see https://github.com/fannheyward/coc-pyright/blob/d58a468b1d7479a1b56906e386f44b997181e307/src/configSettings.ts#L47
        """
        workspace_folder = Path(workspace_folder)

        def binary_from_python_path(path: str | Path) -> Path | None:
            path = Path(path)
            if sublime.platform() == "windows":
                binary_path = path / "Scripts/python.exe"
            else:
                binary_path = path / "bin/python"
            return binary_path if binary_path.is_file() else None

        # Config file, venv resolution command, post-processing
        venv_config_files: list[tuple[str, str, Callable[[str], Path | None] | None]] = [
            (".pdm-python", "pdm info --python", None),
            (".python-version", "pyenv which python", None),
            ("Pipfile", "pipenv --py", None),
            ("poetry.lock", "poetry env info -p", binary_from_python_path),
        ]

        for config_file, command, post_processing in venv_config_files:
            if not (workspace_folder / config_file).is_file():
                continue
            print(f"{cls.name()}: INFO: {config_file} detected. Run subprocess command: {command}")
            try:
                python_path = subprocess.check_output(
                    command,
                    cwd=workspace_folder,
                    shell=True,
                    startupinfo=get_default_startupinfo(),
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                ).strip()
                if post_processing:
                    python_path = post_processing(python_path)
                return Path(python_path) if python_path else None
            except FileNotFoundError:
                print(f"{cls.name()}: WARN: subprocess failed with file not found: {command[0]}")
            except PermissionError as e:
                print(f"{cls.name()}: WARN: subprocess failed with permission error: {e}")
            except subprocess.CalledProcessError as e:
                print(f"{cls.name()}: WARN: subprocess failed: {str(e.output).strip()}")

        # virtual environment as subfolder in project
        for maybe_venv_path in workspace_folder.iterdir():
            try:
                if (maybe_venv_path / "pyvenv.cfg").is_file() and (binary := binary_from_python_path(maybe_venv_path)):
                    return binary  # found a venv
            except PermissionError:
                pass
        return None
