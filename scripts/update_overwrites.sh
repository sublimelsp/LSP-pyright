#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${SCRIPT_DIR}/.."

OVERWRITES_DIR="${PROJECT_DIR}/overwrites"

mkdir -p "${OVERWRITES_DIR}"

update_typeshed() {
    TYPESHED_DIR=${OVERWRITES_DIR}/node_modules/pyright/dist/typeshed-fallback

    # we want to use basedpyright's typeshed stubs for builtins, which has docstrings
    latest_basedpyright=$(
        curl -sI 'https://github.com/DetachHead/basedpyright/releases/latest' |
            perl -ne '/^Location: (.*)$/ && print "$1\n"' |
            sed 's#.*/##' # delete everything before (including) the last slash
    )                     # e.g., "v1.13.0"
    echo "[INFO] Latest basedpyright version: ${latest_basedpyright}"

    if [ -z "${latest_basedpyright}" ]; then
        echo '[ERROR] Failed to get the latest basedpyright version.'
        exit 1
    fi

    curl -sL "https://github.com/DetachHead/basedpyright/releases/download/${latest_basedpyright}/vscode-pyright.vsix" --output 'basedpyright.zip'
    mkdir -p "${TYPESHED_DIR}/stdlib"
    unzip -jo 'basedpyright.zip' 'extension/dist/typeshed-fallback/stdlib/builtins.pyi' -d "${TYPESHED_DIR}/stdlib"
    rm -f 'basedpyright.zip'

    echo '[INFO] typeshed stubs updated.'
}

update_st_api_stubs() {
    SUBLIME_PY33_TYPINGS_DIR="${OVERWRITES_DIR}/resources/typings/sublime_text_py33"

    mkdir -p "${SUBLIME_PY33_TYPINGS_DIR}"

    filenames=(
        '_sublime_types.pyi'
        'sublime.pyi'
        'sublime_plugin.pyi'
    )
    for filename in "${filenames[@]}"; do
        curl -sL \
            "https://raw.githubusercontent.com/jfcherng-sublime/ST-API-stubs/master/typings/${filename}" \
            --output "${SUBLIME_PY33_TYPINGS_DIR}/${filename}"
    done

    echo '[INFO] Sublime Text API stubs updated.'
}

# update_typeshed
update_st_api_stubs
