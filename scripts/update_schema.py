#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.request import urlopen

PACKAGE_NAME = "LSP-pyright"

PROJECT_ROOT = Path(__file__).parents[1]
PYRIGHTCONFIG_SCHEMA_ID = "sublime://pyrightconfig"
PYRIGHT_CONFIGURATION_SCHEMA_URL = (
    "https://raw.githubusercontent.com/microsoft/pyright/main/packages/vscode-pyright/schemas/pyrightconfig.schema.json"  # noqa: E501
)
SUBLIME_PACKAGE_JSON_PATH = PROJECT_ROOT / "sublime-package.json"
# Keys that are in the pyrightconfig.json schema but should not raise a comment when not present in the LSP schema.
IGNORED_PYRIGHTCONFIG_KEYS = {
    "defineConstant",
    "exclude",
    "executionEnvironments",
    "ignore",
    "include",
    "pythonPlatform",
    "pythonVersion",
    "strict",
    "typeshedPath",
    "venv",
    "verboseOutput",
}

JsonDict = dict[str, Any]


def main() -> None:
    json_dump_kwargs = {"indent": 2, "ensure_ascii": False, "sort_keys": True}
    pyrightconfig_schema_json, sublime_package_schema_json = read_sublime_package_json()
    before = json.dumps(sublime_package_schema_json, **json_dump_kwargs)
    new_schema_keys = sorted(update_schema(sublime_package_schema_json, pyrightconfig_schema_json))
    after = json.dumps(sublime_package_schema_json, **json_dump_kwargs)
    if before != after:
        SUBLIME_PACKAGE_JSON_PATH.write_text(f"{after}\n", encoding="utf-8")
        print("sublime-package.json schema updated.")
    else:
        print("No updates done to sublime-package.json.")
    if new_schema_keys:
        new_schema_keys_text = "".join(map(lambda k: f"\n - {k}", new_schema_keys))
        print(f"\nNew keys found in the latest pyrightconfig.json schema: {new_schema_keys_text}\n\n")
        print("Ensure that those are added to the sublime-package.json manually, if relevant.")


def read_sublime_package_json() -> tuple[JsonDict, JsonDict]:
    with urlopen(PYRIGHT_CONFIGURATION_SCHEMA_URL) as response:
        pyrightconfig_schema_json: JsonDict = json.load(response)
    sublime_package_schema_json: JsonDict = json.loads(SUBLIME_PACKAGE_JSON_PATH.read_bytes())
    return (pyrightconfig_schema_json, sublime_package_schema_json)


def update_schema(sublime_package_json: JsonDict, pyrightconfig_schema_json: JsonDict) -> list[str]:
    pyrightconfig_contribution: JsonDict | None = None
    lsp_pyright_contribution: JsonDict | None = None
    for contribution in sublime_package_json["contributions"]["settings"]:
        if "/pyrightconfig.json" in contribution["file_patterns"]:
            pyrightconfig_contribution = contribution
        elif f"/{PACKAGE_NAME}.sublime-settings" in contribution["file_patterns"]:
            lsp_pyright_contribution = contribution
    if not (pyrightconfig_contribution and lsp_pyright_contribution):
        raise Exception("Expected contributions not found in sublime-package.json!")
    # Update to latest pyrightconfig schema.
    pyrightconfig_contribution["schema"] = pyrightconfig_schema_json
    # Add ID.
    pyrightconfig_contribution["schema"]["$id"] = PYRIGHTCONFIG_SCHEMA_ID
    # Update LSP settings to reference options from the pyrightconfig schema.
    # fmt: off
    settings_properties: JsonDict = lsp_pyright_contribution["schema"]["definitions"]["PluginConfig"]["properties"]["settings"]["properties"]  # noqa: E501
    # fmt: on
    pyrightconfig_properties: JsonDict = pyrightconfig_contribution["schema"]["properties"]
    for setting_key, setting_value in settings_properties.items():
        # get last dotted component.
        last_component_key = setting_key.rpartition(".")[2]
        if last_component_key in pyrightconfig_properties:
            update_property_ref(last_component_key, setting_value, pyrightconfig_properties)
        if setting_key == "python.analysis.diagnosticSeverityOverrides":
            overrides_properties: JsonDict = setting_value["properties"]
            for override_key, override_value in overrides_properties.items():
                if override_key in pyrightconfig_properties:
                    update_property_ref(override_key, override_value, pyrightconfig_properties)
                else:
                    del overrides_properties[override_key]
    # Check if there are any properties that might need to be added to the LSP properties.
    # If the property is neither in `diagnosticSeverityOverrides`, the root LSP settings nor in ignored keys
    # then it might have to be added manually.
    all_settings_keys = [key.rpartition(".")[2] for key in settings_properties.keys()]
    all_overrides_keys = settings_properties["python.analysis.diagnosticSeverityOverrides"]["properties"].keys()
    new_schema_keys = []
    for pyrightconfig_key in pyrightconfig_properties.keys():
        if (
            pyrightconfig_key not in all_settings_keys
            and pyrightconfig_key not in all_overrides_keys
            and pyrightconfig_key not in IGNORED_PYRIGHTCONFIG_KEYS
        ):
            new_schema_keys.append(pyrightconfig_key)
    return new_schema_keys


def update_property_ref(property_key: str, property_schema: JsonDict, pyrightconfig_properties: JsonDict) -> None:
    property_schema.clear()
    pyrightconfig_property_id: str = pyrightconfig_properties[property_key]["$id"]
    property_schema["$ref"] = PYRIGHTCONFIG_SCHEMA_ID + pyrightconfig_property_id


if __name__ == "__main__":
    main()
