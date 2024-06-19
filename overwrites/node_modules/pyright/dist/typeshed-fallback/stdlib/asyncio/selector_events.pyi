"""
Event loop using a selector and related classes.

A selector is a "notify-when-ready" multiplexer.  For a subclass which
also includes support for signal handling, see the unix_events sub-module.
"""

import selectors

from . import base_events

__all__ = ("BaseSelectorEventLoop",)

class BaseSelectorEventLoop(base_events.BaseEventLoop):
    """
    Selector event loop.

    See events.EventLoop for API specification.
    """
    def __init__(self, selector: selectors.BaseSelector | None = None) -> None: ...
