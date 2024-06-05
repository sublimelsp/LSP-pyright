from __future__ import annotations

from .constants import PACKAGE_NAME


def log_debug(message: str) -> None:
    print(f"[{PACKAGE_NAME}][DEBUG] {message}")


def log_info(message: str) -> None:
    print(f"[{PACKAGE_NAME}][INFO] {message}")


def log_warning(message: str) -> None:
    print(f"[{PACKAGE_NAME}][WARNING] {message}")


def log_error(message: str) -> None:
    print(f"[{PACKAGE_NAME}][ERROR] {message}")
