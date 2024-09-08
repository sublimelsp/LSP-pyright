from __future__ import annotations

import json
import tempfile
from pathlib import Path

from LSP.plugin.core.collections import DottedDict

from ...utils import run_shell_command
from ..interfaces import BaseDevEnvironmentHandler


class GdbDevEnvironmentHandler(BaseDevEnvironmentHandler):
    def handle_(self, *, settings: DottedDict) -> None:
        self._inject_extra_paths(settings=settings, paths=self.find_paths(settings))

    @classmethod
    def find_paths(cls, settings: DottedDict) -> list[str]:
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "print_sys_path.commands"
            filepath.write_text(
                R"""
python
import sys
import json
json.dump({"executable": sys.executable, "paths": sys.path}, sys.stdout)
end
exit
                """.strip(),
                encoding="utf-8",
            )
            args = (
                cls.get_dev_environment_subsetting(settings, "binary"),
                "--batch",
                "--command",
                str(filepath),
            )
            result = run_shell_command(args, shell=False)

        if not result or result[2] != 0:
            raise RuntimeError(f"Failed to run command: {args}")

        try:
            return json.loads(result[0])["paths"]
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse JSON: {e}")
