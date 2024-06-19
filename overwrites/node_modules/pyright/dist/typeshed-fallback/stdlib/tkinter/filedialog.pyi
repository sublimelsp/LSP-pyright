"""
File selection dialog classes.

Classes:

- FileDialog
- LoadFileDialog
- SaveFileDialog

This module also presents tk common file dialogues, it provides interfaces
to the native file dialogues available in Tk 4.2 and newer, and the
directory dialogue available in Tk 8.3 and newer.
These interfaces were written by Fredrik Lundh, May 1997.
"""

import sys
from _typeshed import Incomplete, StrOrBytesPath
from collections.abc import Iterable
from tkinter import Button, Entry, Frame, Listbox, Misc, Scrollbar, StringVar, Toplevel, commondialog
from typing import IO, ClassVar, Literal

if sys.version_info >= (3, 9):
    __all__ = [
        "FileDialog",
        "LoadFileDialog",
        "SaveFileDialog",
        "Open",
        "SaveAs",
        "Directory",
        "askopenfilename",
        "asksaveasfilename",
        "askopenfilenames",
        "askopenfile",
        "askopenfiles",
        "asksaveasfile",
        "askdirectory",
    ]

dialogstates: dict[Incomplete, tuple[Incomplete, Incomplete]]

class FileDialog:
    """
    Standard file selection dialog -- no checks on selected file.

    Usage:

        d = FileDialog(master)
        fname = d.go(dir_or_file, pattern, default, key)
        if fname is None: ...canceled...
        else: ...open file...

    All arguments to go() are optional.

    The 'key' argument specifies a key in the global dictionary
    'dialogstates', which keeps track of the values for the directory
    and pattern arguments, overriding the values passed in (it does
    not keep track of the default argument!).  If no key is specified,
    the dialog keeps no memory of previous state.  Note that memory is
    kept even when the dialog is canceled.  (All this emulates the
    behavior of the Macintosh file selection dialogs.)
    """
    title: str
    master: Incomplete
    directory: Incomplete | None
    top: Toplevel
    botframe: Frame
    selection: Entry
    filter: Entry
    midframe: Entry
    filesbar: Scrollbar
    files: Listbox
    dirsbar: Scrollbar
    dirs: Listbox
    ok_button: Button
    filter_button: Button
    cancel_button: Button
    def __init__(
        self, master, title: Incomplete | None = None
    ) -> None: ...  # title is usually a str or None, but e.g. int doesn't raise en exception either
    how: Incomplete | None
    def go(self, dir_or_file=".", pattern: str = "*", default: str = "", key: Incomplete | None = None): ...
    def quit(self, how: Incomplete | None = None) -> None: ...
    def dirs_double_event(self, event) -> None: ...
    def dirs_select_event(self, event) -> None: ...
    def files_double_event(self, event) -> None: ...
    def files_select_event(self, event) -> None: ...
    def ok_event(self, event) -> None: ...
    def ok_command(self) -> None: ...
    def filter_command(self, event: Incomplete | None = None) -> None: ...
    def get_filter(self): ...
    def get_selection(self): ...
    def cancel_command(self, event: Incomplete | None = None) -> None: ...
    def set_filter(self, dir, pat) -> None: ...
    def set_selection(self, file) -> None: ...

class LoadFileDialog(FileDialog):
    """File selection dialog which checks that the file exists."""
    title: str
    def ok_command(self) -> None: ...

class SaveFileDialog(FileDialog):
    """File selection dialog which checks that the file may be created."""
    title: str
    def ok_command(self) -> None: ...

class _Dialog(commondialog.Dialog): ...

class Open(_Dialog):
    """Ask for a filename to open"""
    command: ClassVar[str]

class SaveAs(_Dialog):
    """Ask for a filename to save as"""
    command: ClassVar[str]

class Directory(commondialog.Dialog):
    """Ask for a directory"""
    command: ClassVar[str]

# TODO: command kwarg available on macos
def asksaveasfilename(
    *,
    confirmoverwrite: bool | None = ...,
    defaultextension: str | None = ...,
    filetypes: Iterable[tuple[str, str | list[str] | tuple[str, ...]]] | None = ...,
    initialdir: StrOrBytesPath | None = ...,
    initialfile: StrOrBytesPath | None = ...,
    parent: Misc | None = ...,
    title: str | None = ...,
    typevariable: StringVar | str | None = ...,
) -> str:
    """Ask for a filename to save as"""
    ...
def askopenfilename(
    *,
    defaultextension: str | None = ...,
    filetypes: Iterable[tuple[str, str | list[str] | tuple[str, ...]]] | None = ...,
    initialdir: StrOrBytesPath | None = ...,
    initialfile: StrOrBytesPath | None = ...,
    parent: Misc | None = ...,
    title: str | None = ...,
    typevariable: StringVar | str | None = ...,
) -> str:
    """Ask for a filename to open"""
    ...
def askopenfilenames(
    *,
    defaultextension: str | None = ...,
    filetypes: Iterable[tuple[str, str | list[str] | tuple[str, ...]]] | None = ...,
    initialdir: StrOrBytesPath | None = ...,
    initialfile: StrOrBytesPath | None = ...,
    parent: Misc | None = ...,
    title: str | None = ...,
    typevariable: StringVar | str | None = ...,
) -> Literal[""] | tuple[str, ...]:
    """
    Ask for multiple filenames to open

    Returns a list of filenames or empty list if
    cancel button selected
    """
    ...
def askdirectory(
    *, initialdir: StrOrBytesPath | None = ..., mustexist: bool | None = ..., parent: Misc | None = ..., title: str | None = ...
) -> str:
    """Ask for a directory, and return the file name"""
    ...

# TODO: If someone actually uses these, overload to have the actual return type of open(..., mode)
def asksaveasfile(
    mode: str = "w",
    *,
    confirmoverwrite: bool | None = ...,
    defaultextension: str | None = ...,
    filetypes: Iterable[tuple[str, str | list[str] | tuple[str, ...]]] | None = ...,
    initialdir: StrOrBytesPath | None = ...,
    initialfile: StrOrBytesPath | None = ...,
    parent: Misc | None = ...,
    title: str | None = ...,
    typevariable: StringVar | str | None = ...,
) -> IO[Incomplete] | None:
    """Ask for a filename to save as, and returned the opened file"""
    ...
def askopenfile(
    mode: str = "r",
    *,
    defaultextension: str | None = ...,
    filetypes: Iterable[tuple[str, str | list[str] | tuple[str, ...]]] | None = ...,
    initialdir: StrOrBytesPath | None = ...,
    initialfile: StrOrBytesPath | None = ...,
    parent: Misc | None = ...,
    title: str | None = ...,
    typevariable: StringVar | str | None = ...,
) -> IO[Incomplete] | None:
    """Ask for a filename to open, and returned the opened file"""
    ...
def askopenfiles(
    mode: str = "r",
    *,
    defaultextension: str | None = ...,
    filetypes: Iterable[tuple[str, str | list[str] | tuple[str, ...]]] | None = ...,
    initialdir: StrOrBytesPath | None = ...,
    initialfile: StrOrBytesPath | None = ...,
    parent: Misc | None = ...,
    title: str | None = ...,
    typevariable: StringVar | str | None = ...,
) -> tuple[IO[Incomplete], ...]:
    """
    Ask for multiple filenames and return the open file
    objects

    returns a list of open file objects or an empty list if
    cancel selected
    """
    ...
def test() -> None:
    """Simple test program."""
    ...
