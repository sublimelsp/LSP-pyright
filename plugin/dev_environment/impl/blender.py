from __future__ import annotations

import json
import tempfile
from pathlib import Path

from LSP.plugin.core.collections import DottedDict

from ...utils import run_shell_command
from ..interfaces import BaseDevEnvironmentHandler


class BlenderDevEnvironmentHandler(BaseDevEnvironmentHandler):
    def handle_(self, *, settings: DottedDict) -> None:
        self._inject_extra_paths(settings=settings, paths=self.find_paths(settings))

    @classmethod
    def find_paths(cls, settings: DottedDict) -> list[str]:
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "print_sys_path.py"
            filepath.write_text(
                R"""
import sys
import json
json.dump({"executable": sys.executable, "paths": sys.path}, sys.stdout)
exit(0)
                """.strip(),
                encoding="utf-8",
            )
            args = (
                cls.get_dev_environment_subsetting(settings, "binary"),
                "--background",
                "--python",
                str(filepath),
            )
            result = run_shell_command(args, shell=False)

        if not result or result[2] != 0:
            raise RuntimeError(f"Failed to run command: {args}")

        # Blender prints a bunch of general information to stdout before printing the output of the python
        # script. We want to ignore that initial information. We do that by finding the start of the JSON
        # dict. This is a bit hacky and there must be a better way.
        if (index := result[0].find('\n{"')) == -1:
            raise RuntimeError("Unexpected output when calling blender")

        try:
            return json.loads(result[0][index:])["paths"]
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse JSON: {e}")
