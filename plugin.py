import os
import re
import shutil
import subprocess
import sys

import sublime
from LSP.plugin import ClientConfig, DottedDict, MarkdownLangMap, Response, WorkspaceFolder
from LSP.plugin.core.protocol import CompletionItem, Hover, SignatureHelp
from LSP.plugin.core.typing import Any, Callable, List, Optional, Tuple, cast
from lsp_utils import NpmClientHandler
from sublime_lib import ResourcePath

assert __package__

ST_PACKAGES_PATH = sublime.packages_path()


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
        extraPaths = settings.get("python.analysis.extraPaths") or []  # type: List[str]

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
        workspace_folders: List[WorkspaceFolder],
        configuration: ClientConfig,
    ) -> Optional[str]:
        super().on_pre_start(window, initiating_view, workspace_folders, configuration)

        python_path = cls.python_path(configuration.settings, workspace_folders)
        print('{}: INFO: Using python path "{}"'.format(cls.name(), python_path))
        configuration.settings.set("python.pythonPath", python_path)
        return None

    @classmethod
    def install_or_update(cls) -> None:
        super().install_or_update()
        # Copy resources
        src = "Packages/{}/resources/".format(cls.package_name)
        dest = os.path.join(cls.package_storage(), "resources")
        ResourcePath(src).copytree(dest, exist_ok=True)

    @classmethod
    def markdown_language_id_to_st_syntax_map(cls) -> Optional[MarkdownLangMap]:
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
        # Add another linebreak before horizontal rule following fenced code block
        content = re.sub("```\n---", "```\n\n---", content)
        # Add markup for some common field name conventions in function docstring
        content = re.sub(
            r"\n:(\w+)[ \t]+([\w\\*.]+):",
            lambda m: "\n__{field}:__ `{name}`".format(
                field=m.group(1).title(),
                name=m.group(2).replace("\\_", "_").replace("\\*", "*"),
            ),
            content,
        )
        content = re.sub(r"\n:returns?:", r"\n__Returns:__", content)
        content = re.sub(r"\n:rtype:", r"\n__Returntype:__", content)
        content = re.sub(r"\n:deprecated:", r"\n⚠️ __Deprecated:__", content)
        return content

    def detect_st_py_ver(self, dev_environment: str) -> Tuple[int, int]:
        default = (3, 3)

        if dev_environment == "sublime_text_33":
            return (3, 3)
        if dev_environment == "sublime_text_38":
            return (3, 8)

        if dev_environment == "sublime_text":
            session = self.weaksession()
            if not session:
                return default
            workspace_folders = session.get_workspace_folders()
            if not workspace_folders:
                return default
            if workspace_folders[0].path == os.path.join(ST_PACKAGES_PATH, "User"):
                return (3, 8)
            python_version_file = os.path.join(workspace_folders[0].path, ".python-version")
            try:
                with open(python_version_file, "r") as file:
                    if file.read().strip() == "3.8":
                        return (3, 8)
            except Exception:
                pass

        return default

    @classmethod
    def get_plugin_setting(cls, key: str, default: Any = None) -> Any:
        return sublime.load_settings(cls.package_name + ".sublime-settings").get(key, default)

    def find_package_dependency_dirs(self, py_ver: Tuple[int, int] = (3, 3)) -> List[str]:
        dep_dirs = sys.path.copy()

        # replace paths for target Python version
        # @see https://github.com/sublimelsp/LSP-pyright/issues/28
        re_pattern = r"(python3\.?)[38]"
        re_replacement = r"\g<1>8" if py_ver == (3, 8) else r"\g<1>3"
        dep_dirs = [re.sub(re_pattern, re_replacement, d, flags=re.IGNORECASE) for d in dep_dirs]

        # move the "Packages/" to the last
        # @see https://github.com/sublimelsp/LSP-pyright/pull/26#discussion_r520747708
        dep_dirs.remove(ST_PACKAGES_PATH)
        dep_dirs.append(ST_PACKAGES_PATH)

        if py_ver == (3, 3):
            # sublime stubs - add as first
            dep_dirs.insert(0, os.path.join(self.package_storage(), "resources", "typings", "sublime_text"))

        return [path for path in dep_dirs if os.path.isdir(path)]

    @classmethod
    def python_path(cls, settings: DottedDict, workspace_folders: List[WorkspaceFolder]) -> str:
        python_path = settings.get("python.pythonPath")
        if python_path:
            return python_path

        if workspace_folders:
            workspace_folder = os.path.abspath(workspace_folders[0].path)

            while True:
                python_path = cls.python_path_from_venv(workspace_folder)
                if python_path:
                    return python_path

                parent = os.path.dirname(workspace_folder)
                if workspace_folder != parent:
                    workspace_folder = parent
                else:
                    break

        return shutil.which("python") or shutil.which("python3") or ""

    @classmethod
    def python_path_from_venv(cls, workspace_folder: str) -> Optional[str]:
        """
        Resolves the python binary path depending on environment variables and files in the workspace.

        @see https://github.com/fannheyward/coc-pyright/blob/d58a468b1d7479a1b56906e386f44b997181e307/src/configSettings.ts#L47
        """

        def binary_from_python_path(path: str) -> Optional[str]:
            if sublime.platform() == "windows":
                binary_path = os.path.join(path, "Scripts", "python.exe")
            else:
                binary_path = os.path.join(path, "bin", "python")

            return binary_path if os.path.isfile(binary_path) else None

        # Config file, venv resolution command, post-processing
        venv_config_files = [
            (".pdm-python", "pdm info --python", None),
            (".python-version", "pyenv which python", None),
            ("Pipfile", "pipenv --py", None),
            ("poetry.lock", "poetry env info -p", binary_from_python_path),
        ]  # type: List[Tuple[str, str, Optional[Callable[[str], Optional[str]]]]]

        for config_file, command, post_processing in venv_config_files:
            full_config_file_path = os.path.join(workspace_folder, config_file)
            if not os.path.isfile(full_config_file_path):
                continue
            print("{}: INFO: {} detected. Run subprocess command: {}".format(cls.name(), config_file, command))
            try:
                python_path = subprocess.check_output(
                    command,
                    cwd=workspace_folder,
                    shell=True,
                    startupinfo=get_default_startupinfo(),
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                ).strip()
                return post_processing(python_path) if post_processing else python_path
            except FileNotFoundError:
                print("{}: WARN: subprocess failed with file not found: {}".format(cls.name(), command[0]))
            except PermissionError as e:
                print("{}: WARN: subprocess failed with permission error: {}".format(cls.name(), e))
            except subprocess.CalledProcessError as e:
                print("{}: WARN: subprocess failed: {}".format(cls.name(), str(e.output).strip()))

        # virtual environment as subfolder in project
        for file in os.listdir(workspace_folder):
            maybe_venv_path = os.path.join(workspace_folder, file)
            if os.path.isfile(os.path.join(maybe_venv_path, "pyvenv.cfg")):
                binary = binary_from_python_path(maybe_venv_path)
                if binary is not None:
                    return binary  # found a venv

        return None
