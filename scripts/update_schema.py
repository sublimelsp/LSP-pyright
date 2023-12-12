from json import dump, dumps, load
from typing import Any, Dict, List, Optional, Tuple
from urllib.request import urlopen
import os

DIRNAME = os.path.dirname(os.path.abspath(__file__))
PYRIGHTCONFIG_SCHEMA_ID = 'sublime://pyrightconfig'
PYRIGHT_CONFIGURATION_SCHEMA_URL = 'https://raw.githubusercontent.com/microsoft/pyright/main/packages/vscode-pyright/schemas/pyrightconfig.schema.json'  # noqa: E501
SUBLIME_PACKAGE_JSON_PATH = os.path.join(DIRNAME, '..', 'sublime-package.json')
# Keys that are in the pyrightconfig.json schema but should not raise a comment when not present in the LSP schema.
IGNORED_PYRIGHTCONFIG_KEYS = [
    'defineConstant',
    'exclude',
    'executionEnvironments',
    'ignore',
    'include',
    'pythonPlatform',
    'pythonVersion',
    'strict',
    'typeshedPath',
    'venv',
    'verboseOutput',
]

JSON = Dict[str, Any]


def main() -> None:
    pyrightconfig_schema_json, sublime_package_schema_json = read_sublime_package_json()
    before = dumps(sublime_package_schema_json)
    new_schema_keys = update_schema(sublime_package_schema_json, pyrightconfig_schema_json)
    after = dumps(sublime_package_schema_json)
    if before != after:
        with open(SUBLIME_PACKAGE_JSON_PATH, 'w', encoding='utf-8') as f:
            dump(sublime_package_schema_json, f, indent=2)
        print('sublime-package.json schema updated.')
    else:
        print('No updates done to sublime-package.json.')
    if new_schema_keys:
        print('\nThe following new keys were found in the latest pyrightconfig.json schema: {}\n\n'.format(
            '\n - '.join(new_schema_keys)))
        print('Ensure that those are added to the sublime-package.json manually, if relevant.')


def read_sublime_package_json() -> Tuple[JSON, JSON]:
    with urlopen(PYRIGHT_CONFIGURATION_SCHEMA_URL) as response:
        pyrightconfig_schema_json = load(response)
    with open(SUBLIME_PACKAGE_JSON_PATH, 'r', encoding='utf-8') as f:
        sublime_package_schema_json = load(f)
    return (pyrightconfig_schema_json, sublime_package_schema_json)


def update_schema(sublime_package_json: JSON, pyrightconfig_schema_json: JSON) -> List[str]:
    pyrightconfig_contribution: Optional[JSON] = None
    lsp_pyright_contribution: Optional[JSON] = None
    for contribution in sublime_package_json['contributions']['settings']:
        if '/pyrightconfig.json' in contribution['file_patterns']:
            pyrightconfig_contribution = contribution
        elif '/LSP-pyright.sublime-settings' in contribution['file_patterns']:
            lsp_pyright_contribution = contribution
    if not pyrightconfig_contribution or not lsp_pyright_contribution:
        raise Exception('Expected contributions not found in sublime-package.json!')
    # Update to latest pyrightconfig schema.
    pyrightconfig_contribution['schema'] = pyrightconfig_schema_json
    # Add ID.
    pyrightconfig_contribution['schema']['$id'] = PYRIGHTCONFIG_SCHEMA_ID
    # Update LSP settings to reference options from the pyrightconfig schema.
    settings_properties: JSON = lsp_pyright_contribution['schema']['definitions']['PluginConfig']['properties']['settings']['properties']  # noqa: E501
    pyrightconfig_properties: JSON = pyrightconfig_contribution['schema']['properties']
    for setting_key, setting_value in settings_properties.items():
        # get last dotted component.
        last_component_key = setting_key.split('.').pop()
        if last_component_key in pyrightconfig_properties:
            update_property_ref(last_component_key, setting_value, pyrightconfig_properties)
        if setting_key == 'python.analysis.diagnosticSeverityOverrides':
            overrides_properties: JSON = setting_value['properties']
            for override_key, override_value in overrides_properties.items():
                if override_key in pyrightconfig_properties:
                    update_property_ref(override_key, override_value, pyrightconfig_properties)
                else:
                    del overrides_properties[override_key]
    # Check if there are any properties that might need to be added to the LSP properties.
    # If the property is neither in `diagnosticSeverityOverrides`, the root LSP settings nor in ignored keys
    # then it might have to be added manually.
    all_settings_keys = list(map(lambda k: k.split('.').pop(), settings_properties.keys()))
    all_overrides_keys = settings_properties['python.analysis.diagnosticSeverityOverrides']['properties'].keys()
    new_schema_keys = []
    for pyrightconfig_key in pyrightconfig_properties.keys():
        if pyrightconfig_key not in all_settings_keys \
                and pyrightconfig_key not in all_overrides_keys \
                and pyrightconfig_key not in IGNORED_PYRIGHTCONFIG_KEYS:
            new_schema_keys.append(pyrightconfig_key)
    return new_schema_keys


def update_property_ref(property_key: str, property_schema: JSON, pyrightconfig_properties: JSON) -> None:
    property_schema.clear()
    pyrightconfig_property_id: str = pyrightconfig_properties[property_key]['$id']
    property_schema['$ref'] = PYRIGHTCONFIG_SCHEMA_ID + pyrightconfig_property_id


if __name__ == '__main__':
    main()
