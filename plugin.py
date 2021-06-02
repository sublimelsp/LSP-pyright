from LSP.plugin import DottedDict
from LSP.plugin.core.typing import List, Tuple, cast
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

        dev_environment = settings.get("dev_environment")

        if dev_environment in ("sublime_text", "sublime_text_33", "sublime_text_38"):
            if dev_environment == "sublime_text":
                # the Python version this plugin runs on
                py_ver = cast(Tuple[int, int], tuple(sys.version_info[:2]))
            else:
                py_ver = (3, 8) if dev_environment == "sublime_text_38" else (3, 3)

            # add package dependencies into "python.analysis.extraPaths"
            extraPaths = settings.get("python.analysis.extraPaths") or []  # type: List[str]
            extraPaths.extend(self.find_package_dependency_dirs(py_ver))
            settings.set("python.analysis.extraPaths", extraPaths)

    # -------------- #
    # custom methods #
    # -------------- #

    @staticmethod
    def find_package_dependency_dirs(py_ver: Tuple[int, int] = (3, 3)) -> List[str]:
        dep_dirs = sys.path.copy()

        # replace paths for target Python version
        # @see https://github.com/sublimelsp/LSP-pyright/issues/28
        re_pattern = r"(python3\.?)[38]"
        re_replacement = r"\g<1>8" if py_ver == (3, 8) else r"\g<1>3"
        dep_dirs = [re.sub(re_pattern, re_replacement, d, flags=re.IGNORECASE) for d in dep_dirs]

        # move the "Packages/" to the last
        # @see https://github.com/sublimelsp/LSP-pyright/pull/26#discussion_r520747708
        packages_path = sublime.packages_path()
        dep_dirs.remove(packages_path)
        dep_dirs.append(packages_path)

        return [path for path in dep_dirs if os.path.isdir(path)]
