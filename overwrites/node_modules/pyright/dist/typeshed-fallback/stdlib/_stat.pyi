"""
S_IFMT_: file type bits
S_IFDIR: directory
S_IFCHR: character device
S_IFBLK: block device
S_IFREG: regular file
S_IFIFO: fifo (named pipe)
S_IFLNK: symbolic link
S_IFSOCK: socket file
S_IFDOOR: door
S_IFPORT: event port
S_IFWHT: whiteout

S_ISUID: set UID bit
S_ISGID: set GID bit
S_ENFMT: file locking enforcement
S_ISVTX: sticky bit
S_IREAD: Unix V7 synonym for S_IRUSR
S_IWRITE: Unix V7 synonym for S_IWUSR
S_IEXEC: Unix V7 synonym for S_IXUSR
S_IRWXU: mask for owner permissions
S_IRUSR: read by owner
S_IWUSR: write by owner
S_IXUSR: execute by owner
S_IRWXG: mask for group permissions
S_IRGRP: read by group
S_IWGRP: write by group
S_IXGRP: execute by group
S_IRWXO: mask for others (not in group) permissions
S_IROTH: read by others
S_IWOTH: write by others
S_IXOTH: execute by others

UF_NODUMP: do not dump file
UF_IMMUTABLE: file may not be changed
UF_APPEND: file may only be appended to
UF_OPAQUE: directory is opaque when viewed through a union stack
UF_NOUNLINK: file may not be renamed or deleted
UF_COMPRESSED: OS X: file is hfs-compressed
UF_HIDDEN: OS X: file should not be displayed
SF_ARCHIVED: file may be archived
SF_IMMUTABLE: file may not be changed
SF_APPEND: file may only be appended to
SF_NOUNLINK: file may not be renamed or deleted
SF_SNAPSHOT: file is a snapshot file

ST_MODE
ST_INO
ST_DEV
ST_NLINK
ST_UID
ST_GID
ST_SIZE
ST_ATIME
ST_MTIME
ST_CTIME

FILE_ATTRIBUTE_*: Windows file attribute constants
                   (only present on Windows)
"""

import sys
from typing import Literal

SF_APPEND: Literal[0x00040000]
SF_ARCHIVED: Literal[0x00010000]
SF_IMMUTABLE: Literal[0x00020000]
SF_NOUNLINK: Literal[0x00100000]
SF_SNAPSHOT: Literal[0x00200000]

ST_MODE: Literal[0]
ST_INO: Literal[1]
ST_DEV: Literal[2]
ST_NLINK: Literal[3]
ST_UID: Literal[4]
ST_GID: Literal[5]
ST_SIZE: Literal[6]
ST_ATIME: Literal[7]
ST_MTIME: Literal[8]
ST_CTIME: Literal[9]

S_IFIFO: Literal[0o010000]
S_IFLNK: Literal[0o120000]
S_IFREG: Literal[0o100000]
S_IFSOCK: Literal[0o140000]
S_IFBLK: Literal[0o060000]
S_IFCHR: Literal[0o020000]
S_IFDIR: Literal[0o040000]

# These are 0 on systems that don't support the specific kind of file.
# Example: Linux doesn't support door files, so S_IFDOOR is 0 on linux.
S_IFDOOR: int
S_IFPORT: int
S_IFWHT: int

S_ISUID: Literal[0o4000]
S_ISGID: Literal[0o2000]
S_ISVTX: Literal[0o1000]

S_IRWXU: Literal[0o0700]
S_IRUSR: Literal[0o0400]
S_IWUSR: Literal[0o0200]
S_IXUSR: Literal[0o0100]

S_IRWXG: Literal[0o0070]
S_IRGRP: Literal[0o0040]
S_IWGRP: Literal[0o0020]
S_IXGRP: Literal[0o0010]

S_IRWXO: Literal[0o0007]
S_IROTH: Literal[0o0004]
S_IWOTH: Literal[0o0002]
S_IXOTH: Literal[0o0001]

S_ENFMT: Literal[0o2000]
S_IREAD: Literal[0o0400]
S_IWRITE: Literal[0o0200]
S_IEXEC: Literal[0o0100]

UF_APPEND: Literal[0x00000004]
UF_COMPRESSED: Literal[0x00000020]  # OS X 10.6+ only
UF_HIDDEN: Literal[0x00008000]  # OX X 10.5+ only
UF_IMMUTABLE: Literal[0x00000002]
UF_NODUMP: Literal[0x00000001]
UF_NOUNLINK: Literal[0x00000010]
UF_OPAQUE: Literal[0x00000008]

def S_IMODE(mode: int, /) -> int:
    """Return the portion of the file's mode that can be set by os.chmod()."""
    ...
def S_IFMT(mode: int, /) -> int:
    """Return the portion of the file's mode that describes the file type."""
    ...
def S_ISBLK(mode: int, /) -> bool:
    """
    S_ISBLK(mode) -> bool

    Return True if mode is from a block special device file.
    """
    ...
def S_ISCHR(mode: int, /) -> bool:
    """
    S_ISCHR(mode) -> bool

    Return True if mode is from a character special device file.
    """
    ...
def S_ISDIR(mode: int, /) -> bool:
    """
    S_ISDIR(mode) -> bool

    Return True if mode is from a directory.
    """
    ...
def S_ISDOOR(mode: int, /) -> bool:
    """
    S_ISDOOR(mode) -> bool

    Return True if mode is from a door.
    """
    ...
def S_ISFIFO(mode: int, /) -> bool:
    """
    S_ISFIFO(mode) -> bool

    Return True if mode is from a FIFO (named pipe).
    """
    ...
def S_ISLNK(mode: int, /) -> bool:
    """
    S_ISLNK(mode) -> bool

    Return True if mode is from a symbolic link.
    """
    ...
def S_ISPORT(mode: int, /) -> bool:
    """
    S_ISPORT(mode) -> bool

    Return True if mode is from an event port.
    """
    ...
def S_ISREG(mode: int, /) -> bool:
    """
    S_ISREG(mode) -> bool

    Return True if mode is from a regular file.
    """
    ...
def S_ISSOCK(mode: int, /) -> bool:
    """
    S_ISSOCK(mode) -> bool

    Return True if mode is from a socket.
    """
    ...
def S_ISWHT(mode: int, /) -> bool:
    """
    S_ISWHT(mode) -> bool

    Return True if mode is from a whiteout.
    """
    ...
def filemode(mode: int, /) -> str:
    """Convert a file's mode to a string of the form '-rwxrwxrwx'"""
    ...

if sys.platform == "win32":
    IO_REPARSE_TAG_SYMLINK: int
    IO_REPARSE_TAG_MOUNT_POINT: int
    IO_REPARSE_TAG_APPEXECLINK: int

if sys.platform == "win32":
    FILE_ATTRIBUTE_ARCHIVE: Literal[32]
    FILE_ATTRIBUTE_COMPRESSED: Literal[2048]
    FILE_ATTRIBUTE_DEVICE: Literal[64]
    FILE_ATTRIBUTE_DIRECTORY: Literal[16]
    FILE_ATTRIBUTE_ENCRYPTED: Literal[16384]
    FILE_ATTRIBUTE_HIDDEN: Literal[2]
    FILE_ATTRIBUTE_INTEGRITY_STREAM: Literal[32768]
    FILE_ATTRIBUTE_NORMAL: Literal[128]
    FILE_ATTRIBUTE_NOT_CONTENT_INDEXED: Literal[8192]
    FILE_ATTRIBUTE_NO_SCRUB_DATA: Literal[131072]
    FILE_ATTRIBUTE_OFFLINE: Literal[4096]
    FILE_ATTRIBUTE_READONLY: Literal[1]
    FILE_ATTRIBUTE_REPARSE_POINT: Literal[1024]
    FILE_ATTRIBUTE_SPARSE_FILE: Literal[512]
    FILE_ATTRIBUTE_SYSTEM: Literal[4]
    FILE_ATTRIBUTE_TEMPORARY: Literal[256]
    FILE_ATTRIBUTE_VIRTUAL: Literal[65536]

if sys.version_info >= (3, 13):
    SF_SETTABLE: Literal[0x3FFF0000]
    # https://github.com/python/cpython/issues/114081#issuecomment-2119017790
    # SF_RESTRICTED: Literal[0x00080000]
    SF_FIRMLINK: Literal[0x00800000]
    SF_DATALESS: Literal[0x40000000]

    SF_SUPPORTED: Literal[0x9F0000]
    SF_SYNTHETIC: Literal[0xC0000000]

    UF_TRACKED: Literal[0x00000040]
    UF_DATAVAULT: Literal[0x00000080]
    UF_SETTABLE: Literal[0x0000FFFF]
