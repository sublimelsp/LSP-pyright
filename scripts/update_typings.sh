#!/usr/bin/env bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="${SCRIPT_DIR}/.."

SUBLIME_TYPINGS_DIR="${PROJECT_DIR}/resources/typings/sublime_text"

mkdir -p "${SUBLIME_TYPINGS_DIR}"

filenames=(
    "_sublime_typing.pyi"
    "sublime.pyi"
    "sublime_plugin.pyi"
)

for filename in "${filenames[@]}"; do
    curl -L \
        "https://raw.githubusercontent.com/jfcherng-sublime/ST-API-stubs/master/typings/${filename}" \
        --output "${SUBLIME_TYPINGS_DIR}/${filename}"
done

echo "Sublime typings updated"
