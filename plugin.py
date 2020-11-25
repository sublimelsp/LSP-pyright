from LSP.plugin import DottedDict
from LSP.plugin.core.typing import Any, Dict, List, Optional, Tuple
from lsp_utils import notification_handler
from lsp_utils import NpmClientHandler
from sublime_lib import ActivityIndicator
import os
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._activity_indicator = None  # type: Optional[ActivityIndicator]

    @classmethod
    def install_in_cache(cls) -> bool:
        return False

    @classmethod
    def minimum_node_version(cls) -> Tuple[int, int, int]:
        return (12, 0, 0)

    def on_settings_changed(self, settings: DottedDict) -> None:
        super().on_settings_changed(settings)

        if self.get_plugin_setting("dev_environment") == "sublime_text":
            server_settings = settings.get()  # type: Dict[str, Any]

            # add package dependencies into "python.analysis.extraPaths"
            extraPaths = server_settings.get("python.analysis.extraPaths", [])  # type: List[str]
            extraPaths.extend(self.find_package_dependency_dirs())
            server_settings["python.analysis.extraPaths"] = extraPaths

            settings.update(server_settings)

    # ---------------- #
    # message handlers #
    # ---------------- #

    @notification_handler("pyright/beginProgress")
    def handle_begin_progress(self, params) -> None:
        # we don't know why we begin this progress
        # the reason will be updated in "pyright/reportProgress"
        self._start_indicator("{}: Working...".format(self.package_name))

    @notification_handler("pyright/endProgress")
    def handle_end_progress(self, params) -> None:
        self._stop_indicator()

    @notification_handler("pyright/reportProgress")
    def handle_report_progress(self, params: List[str]) -> None:
        self._start_indicator("{}: {}".format(self.package_name, "; ".join(params)))

    # -------------- #
    # custom methods #
    # -------------- #

    @classmethod
    def get_plugin_setting(cls, key: str, default: Optional[Any] = None) -> Any:
        return sublime.load_settings(cls.package_name + ".sublime-settings").get(key, default)

    @staticmethod
    def find_package_dependency_dirs() -> List[str]:
        dep_dirs = sys.path.copy()

        # move the "Packages/" to the last
        # @see https://github.com/sublimelsp/LSP-pyright/pull/26#discussion_r520747708
        packages_path = sublime.packages_path()
        dep_dirs.remove(packages_path)
        dep_dirs.append(packages_path)

        return [path for path in dep_dirs if os.path.isdir(path)]

    def _start_indicator(self, msg: str = "") -> None:
        if self._activity_indicator:
            self._activity_indicator.label = msg  # type: ignore
            self._activity_indicator.update()
        else:
            view = sublime.active_window().active_view()
            if view:
                self._activity_indicator = ActivityIndicator(view, msg)  # type: ignore
                self._activity_indicator.start()

    def _stop_indicator(self) -> None:
        if self._activity_indicator:
            self._activity_indicator.stop()
            self._activity_indicator = None
