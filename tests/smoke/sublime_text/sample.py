import sublime

# The stubs make `ListInputItem` generic, so `value` is an `int` here. Sublime Text's own `sublime.py` types it as
# `Any`, so this error is only reported when the stubs are used.
value: str = sublime.ListInputItem("text", 1).value
