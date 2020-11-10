import os
import sublime

from LSP.plugin.core.typing import Any, Dict, List, Optional, Tuple
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
            configuration["settings"]["python.analysis.extraPaths"].extend(
                [
                    "$packages",
                    os.path.dirname(sublime.__file__),
                ]
            )

    @staticmethod
    def find_package_dependency_dirs() -> List[str]:
        dep_dirs = []  # type: List[str]
        dep_versions = ["all", "st4", "st3", "st2"]
        packages_path = sublime.packages_path()

        for path in os.listdir(packages_path):
            test_package = os.path.join(packages_path, path)

            # is the package a dependency?
            if not (
                os.path.isfile(os.path.join(test_package, ".sublime-dependency"))
                or os.path.isfile(os.path.join(test_package, "dependency-metadata.json"))
            ):
                continue

            for version in dep_versions:
                test_version = os.path.join(test_package, version)

                if os.path.isdir(test_version):
                    dep_dirs.append(test_version)
                    break

        return dep_dirs
