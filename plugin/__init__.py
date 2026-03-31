from __future__ import annotations

from .client import LspPyrightPlugin
from .client import ViewEventListener
from .commands import LspPyrightCreateConfigurationCommand
from .commands import LspPyrightUpdateViewStatusTextCommand

__all__ = (
    # ST: core
    "plugin_loaded",
    "plugin_unloaded",
    # ST: commands
    "LspPyrightCreateConfigurationCommand",
    "LspPyrightUpdateViewStatusTextCommand",
    # ...
    "LspPyrightPlugin",
    "ViewEventListener",
)


def plugin_loaded() -> None:
    """Executed when this plugin is loaded."""
    LspPyrightPlugin.setup()


def plugin_unloaded() -> None:
    """Executed when this plugin is unloaded."""
    LspPyrightPlugin.wf_attrs.clear()
    LspPyrightPlugin.cleanup()
