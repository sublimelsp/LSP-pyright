from _typeshed import SupportsRead
from collections.abc import Callable
from typing import Any

__all__ = ("loads", "load", "TOMLDecodeError")

class TOMLDecodeError(ValueError):
    """An error raised if a document is not valid TOML."""
    ...

def load(fp: SupportsRead[bytes], /, *, parse_float: Callable[[str], Any] = ...) -> dict[str, Any]:
    """Parse TOML from a binary file object."""
    ...
def loads(s: str, /, *, parse_float: Callable[[str], Any] = ...) -> dict[str, Any]:
    """Parse TOML from a string."""
    ...
