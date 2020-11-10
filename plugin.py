import os
import sublime
import sys

from LSP.plugin.core.typing import Any, Dict, List, Tuple
from lsp_utils import NpmClientHandler

from .settings import get_setting


def plugin_loaded() -> None:
    LspPyrightPlugin.setup()


def plugin_unloaded() -> None:
    LspPyrightPlugin.cleanup()


class LspPyrightPlugin(NpmClientHandler):
    package_name = __package__
    server_directory = "language-server"
    server_binary_path = os.path.join(server_directory, "node_modules", "pyright", "langserver.index.js")

    @classmethod
    def install_in_cache(cls) -> bool:
        return False

    @classmethod
    def minimum_node_version(cls) -> Tuple[int, int, int]:
        return (12, 0, 0)

    @classmethod
    def on_client_configuration_ready(cls, configuration: Dict[str, Any]) -> None:
        super().on_client_configuration_ready(configuration)

        if get_setting("st_plugin_development_mode"):
            configuration["settings"]["python.analysis.extraPaths"].extend(cls.find_package_dependency_dirs())

    @staticmethod
    def find_package_dependency_dirs() -> List[str]:
        dep_dirs = sys.path.copy()

        # move the "Packages/" to the last
        # @see https://github.com/sublimelsp/LSP-pyright/pull/26#discussion_r520747708
        packages_path = sublime.packages_path()
        dep_dirs.remove(packages_path)
        dep_dirs.append(packages_path)

        return [path for path in dep_dirs if os.path.isdir(path)]
