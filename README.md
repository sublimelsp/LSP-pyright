# LSP-pyright

Python support for Sublime's LSP plugin provided through [microsoft/pyright](https://github.com/microsoft/pyright).

## Installation

1. Install [LSP](https://packagecontrol.io/packages/LSP) and
   [LSP-pyright](https://packagecontrol.io/packages/LSP-pyright) via Package Control.
2. Restart Sublime.
3. (Optional) Configure pyright for your `virtualenv`.

## Configuration

> **TIP**: It's recommended to additionally install the `LSP-json` package which provides validation and auto-complete for
`LSP-pyright` settings and the `pyrightconfig.json` configuration file.

Here are some ways to configure the package and the language server.

- From `Preferences > Package Settings > LSP > Servers > LSP-pyright`
- From the command palette `Preferences: LSP-pyright Settings`
- Project-specific configuration.
  From the command palette run `Project: Edit Project` and add your settings in:

  ```js
  {
     "settings": {
        "LSP": {
           "LSP-pyright": {
              "settings": {
                 // Put your settings here
              }
           }
        }
     }
  }
  ```

- Through a `pyrightconfig.json` configuration file (check [settings documentation](https://github.com/microsoft/pyright/blob/master/docs/configuration.md))

### Virtual environments

If your project needs to run and be validated within a virtual environment, the `pyrightconfig.json` file needs to be
presented at the root of your project.

The configuration file, at a minimum, should define where your Python virtualenvs are located and the name of the one to
use for your project:

```json
{
    "venvPath": "/path/to/virtualenvs/",
    "venv": "myenv"
}
```

The `venv` option is only supported in the `pyrightconfig.json` file. The `venvPath` can be moved to other places like
project-specific configuration, in case you don't want to hard-code system-specific path in a shared project.

Please see [Pyright Documentation](https://github.com/microsoft/pyright/blob/master/docs/configuration.md) for more options.
