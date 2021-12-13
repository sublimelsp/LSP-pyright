from LSP.plugin import DottedDict, MarkdownLangMap
from LSP.plugin.core.typing import Any, List, Optional, Tuple, cast
from lsp_utils import NpmClientHandler
from sublime_lib import ResourcePath
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
        return (14, 0, 0)

    def on_settings_changed(self, settings: DottedDict) -> None:
        super().on_settings_changed(settings)

        dev_environment = self.get_dev_environment(settings)

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

    @classmethod
    def install_or_update(cls) -> None:
        super().install_or_update()
        # Copy resources
        src = "Packages/{}/resources/".format(cls.package_name)
        dest = os.path.join(cls.package_storage(), "resources")
        ResourcePath(src).copytree(dest, exist_ok=True)

    @classmethod
    def markdown_language_id_to_st_syntax_map(cls) -> Optional[MarkdownLangMap]:
        return {"python": (("python", "py"), ("LSP-pyright/pyright",))}

    # -------------- #
    # custom methods #
    # -------------- #

    @classmethod
    def get_dev_environment(cls, settings: DottedDict) -> str:
        # "dev_environment" has been deprecated, use "pyright.dev_environment" instead
        dev_environment = cls.get_plugin_setting("dev_environment")
        if dev_environment is None:
            dev_environment = settings.get("pyright.dev_environment")

        return dev_environment

    @classmethod
    def get_plugin_setting(cls, key: str, default: Optional[Any] = None) -> Any:
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
        packages_path = sublime.packages_path()
        dep_dirs.remove(packages_path)
        dep_dirs.append(packages_path)

        # sublime stubs - add as first
        dep_dirs.insert(0, os.path.join(self.package_storage(), "resources", "typings", "sublime_text"))

        return [path for path in dep_dirs if os.path.isdir(path)]
