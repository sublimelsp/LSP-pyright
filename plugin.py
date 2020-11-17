import os
import sublime
import sys

from LSP.plugin.core.typing import Any, Dict, List, Tuple
from lsp_utils import NpmClientHandler


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
    def on_settings_read(cls, settings: sublime.Settings) -> bool:
        super().on_settings_read(settings)

        if settings.get("dev_environment") == "sublime_text":
            server_settings = settings.get("settings", {})  # type: Dict[str, Any]

            # add package dependencies into "python.analysis.extraPaths"
            extraPaths = server_settings.get("python.analysis.extraPaths", [])  # type: List[str]
            extraPaths.extend(cls.find_package_dependency_dirs())
            server_settings["python.analysis.extraPaths"] = extraPaths

            settings.set("settings", server_settings)

        return False

    def on_ready(self, api) -> None:
        api.on_notification("pyright/beginProgress", self.handle_begin_progress)
        api.on_notification("pyright/endProgress", self.handle_end_progress)
        api.on_notification("pyright/reportProgress", self.handle_report_progress)

    def handle_begin_progress(self, params) -> None:
        sublime.status_message("{}: Progress begins".format(self.package_name))

    def handle_end_progress(self, params) -> None:
        sublime.status_message("{}: Progress ends".format(self.package_name))

    def handle_report_progress(self, params: List[str]) -> None:
        sublime.status_message("{}: {}".format(self.package_name, "; ".join(params)))

    @staticmethod
    def find_package_dependency_dirs() -> List[str]:
        dep_dirs = sys.path.copy()

        # move the "Packages/" to the last
        # @see https://github.com/sublimelsp/LSP-pyright/pull/26#discussion_r520747708
        packages_path = sublime.packages_path()
        dep_dirs.remove(packages_path)
        dep_dirs.append(packages_path)

        return [path for path in dep_dirs if os.path.isdir(path)]
