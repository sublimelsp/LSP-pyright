#!/usr/bin/env bash

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
SUBLIME_STUBS_DIR="$( cd "${SCRIPT_DIR}/../typings/sublime_text" && pwd )"

for filename in sublime sublime_plugin _sublime_typing
do
    curl -L https://raw.githubusercontent.com/jfcherng-sublime/ST-API-stubs/master/typings/${filename}.pyi --output "$SUBLIME_STUBS_DIR/${filename}.pyi"
done

echo "Sublime stubs updated"
