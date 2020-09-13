import os
import sublime

from LSP.plugin.core.typing import Dict, Optional, Tuple
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
    def additional_variables(cls) -> Optional[Dict[str, str]]:
        variables = {}
        variables["sublime_py_files_dir"] = os.path.dirname(sublime.__file__)
        return variables

    @classmethod
    def minimum_node_version(cls) -> Tuple[int, int, int]:
        return (12, 0, 0)
