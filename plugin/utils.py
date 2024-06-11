from __future__ import annotations

import os
import re
import subprocess
from typing import Any


def get_default_startupinfo() -> Any:
    if os.name == "nt":
        # do not create a window for the process
        STARTUPINFO = subprocess.STARTUPINFO()  # type: ignore
        STARTUPINFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # type: ignore
        STARTUPINFO.wShowWindow = subprocess.SW_HIDE  # type: ignore
        return STARTUPINFO
    return None


def lowercase_drive_letter(path: str) -> str:
    return re.sub(r"^[A-Z]+(?=:\\)", lambda m: m.group(0).lower(), path)
