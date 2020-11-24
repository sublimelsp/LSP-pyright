from LSP.plugin import __version__ as lsp_version
from LSP.plugin import DottedDict
from LSP.plugin.core.typing import Any, Dict, List, Optional, Tuple
from lsp_utils import NpmClientHandler
from sublime_lib import ActivityIndicator
import os
import sublime
import sys


def plugin_loaded() -> None:
    LspPyrightPlugin.setup()


def plugin_unloaded() -> None:
    LspPyrightPlugin.cleanup()


def deflate_dict(d: Dict[str, Any], sep: str = ".", prefix: str = "") -> Dict[str, Any]:
    """
    Deflated a nested dict into a single-level dict.

    Converts `{"a":{"b":{"c":"d"}}}`` into `{"a.b.c":"d"}`.

    :param      d:       The source dict
    :param      sep:     The key separator
    :param      prefix:  The key prefix
    """

    d_new = {}

    for k, v in d.items():
        prefix_next = (prefix + sep + k) if prefix else k

        if isinstance(v, dict):
            d_new.update(deflate_dict(v, sep, prefix_next))
        else:
            d_new[prefix_next] = v

    return d_new


class LspPyrightPlugin(NpmClientHandler):
    package_name = __package__
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

    @classmethod
    def on_settings_read(cls, settings: sublime.Settings) -> bool:
        """ Only needed for ST 3 """

        super().on_settings_read(settings)

        if lsp_version < (1, 0, 0) and cls.get_dev_environment() == "sublime_text":
            server_settings = settings.get("settings", {})  # type: Dict[str, Any]
            cls.inject_extra_paths_st(server_settings)
            settings.set("settings", server_settings)

        return False

    def on_settings_changed(self, settings: DottedDict) -> None:
        """ Only works for ST 4 """

        super().on_settings_changed(settings)

        if self.get_dev_environment() == "sublime_text":
            server_settings = deflate_dict(settings.get())
            self.inject_extra_paths_st(server_settings)
            settings.update(server_settings)

    def on_ready(self, api) -> None:
        api.on_notification("pyright/beginProgress", self.handle_begin_progress)
        api.on_notification("pyright/endProgress", self.handle_end_progress)
        api.on_notification("pyright/reportProgress", self.handle_report_progress)

    def handle_begin_progress(self, params) -> None:
        # we don't know why we begin this progress
        # the reason will be updated in "pyright/reportProgress"
        self._start_indicator("{}: Working...".format(self.package_name))

    def handle_end_progress(self, params) -> None:
        self._stop_indicator()

    def handle_report_progress(self, params: List[str]) -> None:
        self._start_indicator("{}: {}".format(self.package_name, "; ".join(params)))

    @classmethod
    def get_dev_environment(cls, settings: Optional[sublime.Settings] = None) -> str:
        if not settings:
            settings = sublime.load_settings(cls.package_name + ".sublime-settings")

        return str(settings.get("dev_environment"))

    @classmethod
    def inject_extra_paths_st(cls, server_settings: Dict[str, Any]) -> None:
        # add package dependencies into "python.analysis.extraPaths"
        extraPaths = server_settings.get("python.analysis.extraPaths", [])  # type: List[str]
        extraPaths.extend(cls.find_package_dependency_dirs())
        server_settings["python.analysis.extraPaths"] = extraPaths

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
