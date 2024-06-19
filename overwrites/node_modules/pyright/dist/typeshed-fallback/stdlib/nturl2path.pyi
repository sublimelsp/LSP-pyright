"""
Convert a NT pathname to a file URL and vice versa.

This module only exists to provide OS-specific code
for urllib.requests, thus do not use directly.
"""

def url2pathname(url: str) -> str:
    """
    OS-specific conversion from a relative URL of the 'file' scheme
    to a file system path; not recommended for general use.
    """
    ...
def pathname2url(p: str) -> str:
    """
    OS-specific conversion from a file system path to a relative URL
    of the 'file' scheme; not recommended for general use.
    """
    ...
