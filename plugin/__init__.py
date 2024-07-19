from __future__ import annotations

from .client import LspPyrightPlugin
from .commands import LspPyrightCreateConfigurationCommand

__all__ = (
    # ST: core
    "plugin_loaded",
    "plugin_unloaded",
    # ST: commands
    "LspPyrightCreateConfigurationCommand",
    # ...
    "LspPyrightPlugin",
)


def plugin_loaded() -> None:
    """Executed when this plugin is loaded."""
    LspPyrightPlugin.setup()


def plugin_unloaded() -> None:
    """Executed when this plugin is unloaded."""
    LspPyrightPlugin.window_attrs.clear()
    LspPyrightPlugin.cleanup()
