from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
import weakref
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, cast

import jmespath
import sublime
from LSP.plugin import ClientConfig, DottedDict, MarkdownLangMap, Response, WorkspaceFolder
from LSP.plugin.core.protocol import CompletionItem, Hover, SignatureHelp
from lsp_utils import NpmClientHandler
from more_itertools import first_true
from sublime_lib import ResourcePath

from .constants import PACKAGE_NAME
from .log import log_error, log_info, log_warning
from .template import load_string_template
from .utils import run_shell_command
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

        dev_environment = settings.get("pyright.dev_environment")
        extra_paths: list[str] = settings.get("python.analysis.extraPaths") or []

        try:
            if dev_environment.startswith("sublime_text"):
                py_ver = self.detect_st_py_ver(dev_environment)
                # add package dependencies into "python.analysis.extraPaths"
                extra_paths.extend(self.find_package_dependency_dirs(py_ver))
            elif dev_environment == "blender":
                extra_paths.extend(self.find_blender_paths(settings))
            elif dev_environment == "gdb":
                extra_paths.extend(self.find_gdb_paths(settings))
            settings.set("python.analysis.extraPaths", extra_paths)
        except Exception as ex:
            log_error(f"failed to update extra paths for dev environment {dev_environment}: {ex}")
        finally:
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
        if py_ver == (3, 3) and (server_dir := self._server_directory_path()):
            dep_dirs.insert(0, os.path.join(server_dir, "resources", "typings", "sublime_text_py33"))

        return list(filter(os.path.isdir, dep_dirs))

    @classmethod
    def _print_print_sys_paths(cls, sink: Callable[[str], None]) -> None:
        sink("import sys")
        sink("import json")
        sink('json.dump({"executable": sys.executable, "paths": sys.path}, sys.stdout)')

    @classmethod
    def _get_dev_environment_binary(cls, settings: DottedDict, name: str) -> str:
        return settings.get(f"settings.dev_environment.{name}.binary") or name

    @classmethod
    def _check_json_is_dict(cls, name: str, output_dict: Any) -> dict[str, Any]:
        if not isinstance(output_dict, dict):
            raise RuntimeError(f"unexpected output when calling {name}; expected JSON dict")
        return output_dict

    @classmethod
    def find_blender_paths(cls, settings: DottedDict) -> list[str]:
        filename = "print_sys_path.py"
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, filename)
            with open(filepath, "w") as fp:

                def out(line: str) -> None:
                    print(line, file=fp)

                cls._print_print_sys_paths(out)
                out("exit(0)")
            args = (cls._get_dev_environment_binary(settings, "blender"), "--background", "--python", filepath)
            result = run_shell_command(args, shell=False)
        if result is None or result[2] != 0:
            raise RuntimeError("failed to run command")
        # Blender prints a bunch of general information to stdout before printing the output of the python
        # script. We want to ignore that initial information. We do that by finding the start of the JSON
        # dict. This is a bit hacky and there must be a better way.
        index = result[0].find('\n{"')
        if index == -1:
            raise RuntimeError("unexpected output when calling blender")
        return cls._check_json_is_dict("blender", json.loads(result[0][index:].strip()))["paths"]

    @classmethod
    def find_gdb_paths(cls, settings: DottedDict) -> list[str]:
        filename = "print_sys_path.commands"
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, filename)
            with open(filepath, "w") as fp:

                def out(line: str) -> None:
                    print(line, file=fp)

                out("python")
                cls._print_print_sys_paths(out)
                out("end")
                out("exit")
            args = (cls._get_dev_environment_binary(settings, "gdb"), "--batch", "--command", filepath)
            result = run_shell_command(args, shell=False)
        if result is None or result[2] != 0:
            raise RuntimeError("failed to run command")
        return cls._check_json_is_dict("gdb", json.loads(result[0].strip()))["paths"]

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

        def _update_simple_python_path() -> None:
            window_attr.simple_python_executable = None

            if python_path := first_true(("py", "python3", "python"), pred=shutil.which):
                window_attr.simple_python_executable = Path(python_path)

        _update_simple_python_path()
        _update_venv_info()
