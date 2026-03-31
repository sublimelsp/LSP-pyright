from __future__ import annotations

from ..client import LspPyrightPlugin
from ..constants import PACKAGE_NAME
from ..log import log_warning
from ..template import load_string_template
from ..utils_lsp import find_workspace_folder
from LSP.plugin import LspTextCommand
from typing import Any
from typing import final
from typing_extensions import override
import sublime


@final
class LspPyrightUpdateViewStatusTextCommand(LspTextCommand):
    session_name = PACKAGE_NAME

    @override
    def run(self, edit: sublime.Edit) -> None:
        session = self.session_by_name()
        if session is None:
            return

        if not (file_path := self.view.file_name()) or not (window := self.view.window()):
            return

        # shortcut if the user doesn't want any status text
        if not (template_text := str(session.config.settings.get("statusText") or "")):
            session.set_config_status_async("")
            return

        variables: dict[str, Any] = {
            "server_version": LspPyrightPlugin.server_version,
        }

        if (
            (wf_path := find_workspace_folder(window, file_path))
            and (wf_attr := LspPyrightPlugin.wf_attrs.get(wf_path))
            and (venv_info := wf_attr.venv_info)
        ):
            variables["venv"] = {
                "finder_name": venv_info.meta.finder_name,
                "python_version": venv_info.python_version,
                "venv_prompt": venv_info.prompt,
            }

        rendered_text = ""
        try:
            rendered_text = load_string_template(template_text).render(variables)
        except Exception as e:
            log_warning(f'Invalid "statusText" template: {e}')

        session.set_config_status_async(rendered_text)
