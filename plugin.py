import os
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
