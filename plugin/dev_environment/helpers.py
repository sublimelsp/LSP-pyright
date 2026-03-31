from __future__ import annotations

from .impl import BlenderDevEnvironmentHandler
from .impl import GdbDevEnvironmentHandler
from .impl import SublimeTextDevEnvironmentHandler
from .impl import VERSIONED_SUBLIME_TEXT_DEV_ENVIRONMENT_HANDLERS
from .interfaces import BaseDevEnvironmentHandler
from more_itertools import first_true
from pathlib import Path
from typing import Generator
from typing import Sequence


def find_dev_environment_handler_class(dev_environment: str) -> type[BaseDevEnvironmentHandler] | None:
    return first_true(
        list_dev_environment_handler_classes(),
        pred=lambda handler_cls: handler_cls.can_support(dev_environment),
    )


def get_dev_environment_handler(
    dev_environment: str,
    *,
    server_dir: str | Path,
    workspace_folders: Sequence[str],
) -> BaseDevEnvironmentHandler | None:
    if handler_cls := find_dev_environment_handler_class(dev_environment):
        return handler_cls(server_dir=server_dir, workspace_folders=workspace_folders)
    return None


def list_dev_environment_handler_classes() -> Generator[type[BaseDevEnvironmentHandler], None, None]:
    yield BlenderDevEnvironmentHandler
    yield GdbDevEnvironmentHandler
    yield from VERSIONED_SUBLIME_TEXT_DEV_ENVIRONMENT_HANDLERS  # sublime_text_33, sublime_text_38, etc
    yield SublimeTextDevEnvironmentHandler  # sublime_text
