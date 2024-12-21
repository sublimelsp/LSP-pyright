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
            dumped_result = Path(tmpdir) / "sys_path.json"
            dumper_path = Path(tmpdir) / "sys_path_dumper.py"
            dumper_path.write_text(
                Rf"""
import sys
import json
with open("{dumped_result}", "w", encoding="utf-8") as f:
    json.dump({{"executable": sys.executable, "paths": sys.path}}, f)
exit(0)
                """.strip(),
                encoding="utf-8",
            )
            args = (
                cls.get_dev_environment_subsetting(settings, "binary"),
                "--background",
                "--python",
                str(dumper_path),
            )
            result = run_shell_command(args, shell=False)

            if not result or result[2] != 0:
                raise RuntimeError(f"Failed to run command: {args}")

            return json.loads(dumped_result.read_bytes())["paths"]
