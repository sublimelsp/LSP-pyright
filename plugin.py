import os
import sublime

from LSP.plugin.core.typing import Dict, Optional
from lsp_utils import NpmClientHandler


def plugin_loaded():
    LspPyrightPlugin.setup()


def plugin_unloaded():
    LspPyrightPlugin.cleanup()


class LspPyrightPlugin(NpmClientHandler):
    package_name = __package__
    server_directory = "language-server"
    server_binary_path = os.path.join(
        server_directory, "node_modules", "pyright", "langserver.index.js"
    )

    @classmethod
    def additional_variables(cls) -> Optional[Dict[str, str]]:
        variables = {}
        variables["sublime_py_files_dir"] = os.path.dirname(sublime.__file__)
        variables["sublime_packages_dir"] = sublime.packages_path()
        return variables
