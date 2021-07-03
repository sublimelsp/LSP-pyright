#!/usr/bin/env bash

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
SUBLIME_TYPINGS_DIR="$( cd "${SCRIPT_DIR}/../resources/typings/sublime_text" && pwd )"

for filename in sublime sublime_plugin _sublime_typing
do
    curl -L https://raw.githubusercontent.com/jfcherng-sublime/ST-API-stubs/master/typings/${filename}.pyi --output "$SUBLIME_TYPINGS_DIR/${filename}.pyi"
done

echo "Sublime typings updated"
