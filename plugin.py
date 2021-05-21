from LSP.plugin import DottedDict
from LSP.plugin.core.typing import Any, List, Optional, Tuple
from lsp_utils import NpmClientHandler
import os
import re
import sublime
import sys


def plugin_loaded() -> None:
    LspPyrightPlugin.setup()


def plugin_unloaded() -> None:
    LspPyrightPlugin.cleanup()


class LspPyrightPlugin(NpmClientHandler):
    package_name = __package__.split(".")[0]
    server_directory = "language-server"
    server_binary_path = os.path.join(server_directory, "node_modules", "pyright", "langserver.index.js")

    @classmethod
    def minimum_node_version(cls) -> Tuple[int, int, int]:
        return (12, 0, 0)

    def on_settings_changed(self, settings: DottedDict) -> None:
        super().on_settings_changed(settings)

        dev_environment = self.get_plugin_setting("dev_environment")

        if dev_environment in ("sublime_text", "sublime_text_33", "sublime_text_38"):
            py_ver = "38" if dev_environment == "sublime_text_38" else "33"

            # add package dependencies into "python.analysis.extraPaths"
            extraPaths = settings.get("python.analysis.extraPaths") or []  # type: List[str]
            extraPaths.extend(self.find_package_dependency_dirs(py_ver))
            settings.set("python.analysis.extraPaths", extraPaths)

    # -------------- #
    # custom methods #
    # -------------- #

    @classmethod
    def get_plugin_setting(cls, key: str, default: Optional[Any] = None) -> Any:
        return sublime.load_settings(cls.package_name + ".sublime-settings").get(key, default)

    @staticmethod
    def find_package_dependency_dirs(py_ver: str = "33") -> List[str]:
        dep_dirs = sys.path.copy()

        if py_ver == "38":
            dep_dirs = [re.sub(r"(python3\.?)3", r"\g<1>8", d, flags=re.IGNORECASE) for d in dep_dirs]

        # move the "Packages/" to the last
        # @see https://github.com/sublimelsp/LSP-pyright/pull/26#discussion_r520747708
        packages_path = sublime.packages_path()
        dep_dirs.remove(packages_path)
        dep_dirs.append(packages_path)

        return [path for path in dep_dirs if os.path.isdir(path)]
