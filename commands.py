from LSP.plugin.core.typing import List
from os import path
import sublime
import sublime_plugin


CONFIGURATION_FILENAME = 'pyrightconfig.json'
CONFIGURATION_CONTENTS = '''{
\t// Install LSP-json to get validation and autocompletion in this file.
\t"venvPath": ".",
\t"venv": "myenv",
}
'''


class LspPyrightCreateConfiguration(sublime_plugin.WindowCommand):
    def run(self) -> None:
        folders = self.window.folders()
        if len(folders) == 0:
            sublime.message_dialog('No folders found in the window. Please add a folder first.')
        elif len(folders) == 1:
            self._create_configuration(folders[0])
        else:
            self.window.show_quick_panel(folders, lambda index: self._on_selected(folders, index),
                                         placeholder='Select a folder to create the configuration file in')

    def _on_selected(self, folders: List[str], index: int) -> None:
        if index > -1:
            self._create_configuration(folders[index])

    def _create_configuration(self, folder_path: str) -> None:
        config_path = path.join(folder_path, CONFIGURATION_FILENAME)
        new_view = self.window.open_file(config_path)
        if not path.isfile(config_path):
            self._poll_view_until_loaded(new_view)

    def _poll_view_until_loaded(self, view: sublime.View, attempt: int = 1) -> None:
        if attempt > 10:
            return
        if view.is_loading():
            sublime.set_timeout(lambda: self._poll_view_until_loaded(view, attempt + 1), 100)
        else:
            self._on_view_loaded(view)

    def _on_view_loaded(self, view: sublime.View) -> None:
        view.run_command('insert_snippet', {'contents': CONFIGURATION_CONTENTS})
