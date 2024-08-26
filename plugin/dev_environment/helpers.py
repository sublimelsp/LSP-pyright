from __future__ import annotations

from pathlib import Path
from typing import Generator, Sequence

from more_itertools import first_true

from .impl import (
    BlenderDevEnvironmentHandler,
    GdbDevEnvironmentHandler,
    SublimeText33DevEnvironmentHandler,
    SublimeText38DevEnvironmentHandler,
    SublimeTextDevEnvironmentHandler,
)
from .interfaces import BaseDevEnvironmentHandler


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
        return handler_cls(
            server_dir=server_dir,
            workspace_folders=workspace_folders,
        )
    return None


def list_dev_environment_handler_classes() -> Generator[type[BaseDevEnvironmentHandler], None, None]:
    yield BlenderDevEnvironmentHandler
    yield GdbDevEnvironmentHandler
    yield SublimeText33DevEnvironmentHandler
    yield SublimeText38DevEnvironmentHandler
    yield SublimeTextDevEnvironmentHandler
