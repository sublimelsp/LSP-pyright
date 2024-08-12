from __future__ import annotations

from pathlib import Path
from typing import Sequence

from more_itertools import first_true

from .venv_finder import find_finder_class_by_name
from .venv_info import BaseVenvInfo, list_venv_info_classes


def find_venv_by_finder_names(finder_names: Sequence[str], *, project_dir: Path) -> BaseVenvInfo | None:
    """Finds the virtual environment information by finders."""
    if isinstance(finder_names, str):
        finder_names = (finder_names,)

    for finder_name in finder_names:
        if (
            (finder_cls := find_finder_class_by_name(finder_name))
            and finder_cls.can_support(project_dir)
            and (venv_info := finder_cls(project_dir).find_venv())
        ):
            return venv_info
    return None


def find_venv_by_python_executable(python_executable: str | Path) -> BaseVenvInfo | None:
    """Finds the virtual environment information by the Python executable path."""
    return first_true(
        map(
            lambda cls: cls.from_python_executable(python_executable),
            list_venv_info_classes(),
        ),
    )
