# LSP-pyright

Python support for Sublime's LSP plugin provided through [microsoft/pyright](https://github.com/microsoft/pyright). 

## Installation

1. Install [LSP](https://packagecontrol.io/packages/LSP) and
   [LSP-pyright](https://packagecontrol.io/packages/LSP-pyright) via Package Control.
1. Restart Sublime.
1. Configure pyright for your virtualenv.

## Configuration

There are some ways to configure the package and the language server.

- From `Preferences > Package Settings > LSP > Servers > LSP-pyright`
- From the command palette `Preferences: LSP-pyright Settings`

Project specific settings can also be set for LSP-pyright (and all LSP plugins):

- From the command palette `Project: Edit Project`

Your project will also require a `pyrightconfig.json` file, usually in the project root.

At a minimum, the file should define where your Python virtualenvs are located and the name of the one to use for your project:

```json
{
    "venvPath": "/path/to/virtualenvs/",
    "venv": "env"
}
```
Please see the [Pyright Docs](https://github.com/microsoft/pyright/blob/master/docs/configuration.md) for more options.
