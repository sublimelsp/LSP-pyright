from __future__ import annotations

import io
import os
import subprocess
import sys
from collections.abc import Generator, Iterable
from pathlib import Path
from typing import Any, Sequence, TypeVar

from .log import log_error

_T = TypeVar("_T")


def camel_to_snake(s: str) -> str:
    """Converts "CamelCase" to "snake_case"."""
    return "".join((f"_{c}" if c.isupper() else c) for c in s).strip("_").lower()


def snake_to_camel(s: str, *, upper_first: bool = True) -> str:
    """Converts "snake_case" to "CamelCase"."""
    first, *others = s.split("_")
    return (first.title() if upper_first else first.lower()) + "".join(map(str.title, others))


if sys.version_info >= (3, 9):
    remove_prefix = str.removeprefix
    remove_suffix = str.removesuffix
else:

    def remove_prefix(s: str, prefix: str) -> str:
        """Remove the prefix from the string. I.e., str.removeprefix in Python 3.9."""
        return s[len(prefix) :] if s.startswith(prefix) else s

    def remove_suffix(s: str, suffix: str) -> str:
        """Remove the suffix from the string. I.e., str.removesuffix in Python 3.9."""
        # suffix="" should not call s[:-0]
        return s[: -len(suffix)] if suffix and s.endswith(suffix) else s


def drop_falsy(iterable: Iterable[_T | None]) -> Generator[_T, None, None]:
    """Drops falsy values from the iterable."""
    yield from filter(None, iterable)


def iterate_by_line(s: str) -> Generator[str, None, None]:
    """Iterates over lines of the string."""
    with io.StringIO(s) as f:
        yield from f


def get_default_startupinfo() -> Any:
    if os.name == "nt":
        # do not create a window for the process
        STARTUPINFO = subprocess.STARTUPINFO()  # type: ignore
        STARTUPINFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # type: ignore
        STARTUPINFO.wShowWindow = subprocess.SW_HIDE  # type: ignore
        return STARTUPINFO
    return None


def run_shell_command(
    command: str | Sequence[str], *, cwd: str | Path | None = None, shell: bool = True
) -> tuple[str, str, int] | None:
    try:
        proc = subprocess.Popen(
            command,
            cwd=cwd,
            shell=shell,
            startupinfo=get_default_startupinfo(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        stdout, stderr = map(str.rstrip, proc.communicate())
    except Exception as e:
        log_error(f"Failed running command ({command}): {e}")
        return None

    if stderr:
        log_error(f"Failed running command ({command}): {stderr}")

    return stdout, stderr, proc.returncode or 0
