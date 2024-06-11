from __future__ import annotations

import sublime
import sublime_plugin

from .client import LspPyrightPlugin


class PyrightEventListener(sublime_plugin.EventListener):
    def on_pre_close_window(self, window: sublime.Window) -> None:
        LspPyrightPlugin.window_attrs.pop(window.id(), None)
