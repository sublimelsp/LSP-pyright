import sys
from tkinter.commondialog import Dialog
from typing import ClassVar, Final

if sys.version_info >= (3, 9):
    __all__ = [
        "showinfo",
        "showwarning",
        "showerror",
        "askquestion",
        "askokcancel",
        "askyesno",
        "askyesnocancel",
        "askretrycancel",
    ]

ERROR: Final = "error"
INFO: Final = "info"
QUESTION: Final = "question"
WARNING: Final = "warning"
ABORTRETRYIGNORE: Final = "abortretryignore"
OK: Final = "ok"
OKCANCEL: Final = "okcancel"
RETRYCANCEL: Final = "retrycancel"
YESNO: Final = "yesno"
YESNOCANCEL: Final = "yesnocancel"
ABORT: Final = "abort"
RETRY: Final = "retry"
IGNORE: Final = "ignore"
CANCEL: Final = "cancel"
YES: Final = "yes"
NO: Final = "no"

class Message(Dialog):
    """A message box"""
    command: ClassVar[str]

def showinfo(title: str | None = None, message: str | None = None, **options) -> str:
    """Show an info message"""
    ...
def showwarning(title: str | None = None, message: str | None = None, **options) -> str:
    """Show a warning message"""
    ...
def showerror(title: str | None = None, message: str | None = None, **options) -> str:
    """Show an error message"""
    ...
def askquestion(title: str | None = None, message: str | None = None, **options) -> str:
    """Ask a question"""
    ...
def askokcancel(title: str | None = None, message: str | None = None, **options) -> bool:
    """Ask if operation should proceed; return true if the answer is ok"""
    ...
def askyesno(title: str | None = None, message: str | None = None, **options) -> bool:
    """Ask a question; return true if the answer is yes"""
    ...
def askyesnocancel(title: str | None = None, message: str | None = None, **options) -> bool | None:
    """Ask a question; return true if the answer is yes, None if cancelled."""
    ...
def askretrycancel(title: str | None = None, message: str | None = None, **options) -> bool:
    """Ask if operation should be retried; return true if the answer is yes"""
    ...
