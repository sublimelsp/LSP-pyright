import sublime

from LSP.plugin.core.typing import Any, Optional


def get_settings_file() -> str:
    """
    @brief Get the settings file name.

    @return The settings file name.
    """

    # __package__ will be "THE_PLUGIN_NAME.plugin" under this folder structure
    # anyway, the top module should always be the plugin name
    return __package__.partition(".")[0] + ".sublime-settings"


def get_settings_object() -> sublime.Settings:
    """
    @brief Get the plugin settings object. This function will call `sublime.load_settings()`.

    @return The settings object.
    """

    return sublime.load_settings(get_settings_file())


def get_setting(key: str, default: Optional[Any] = None) -> Any:
    """
    @brief Get a specific plugin setting.

    @return The setting value, the default value otherwise.
    """

    return get_settings_object().get(key, default)
