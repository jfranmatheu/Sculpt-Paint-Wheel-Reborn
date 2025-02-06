# File System util functions.
from pathlib import Path
import ctypes
import platform


def is_junction(path: Path) -> bool:
    # Check if the path exists
    if not path.exists():
        return False

    if platform.system() != 'Windows':
        return False

    # Use GetFileAttributes to check if it's a reparse point and a directory
    file_attributes = ctypes.windll.kernel32.GetFileAttributesW(str(path))

    if file_attributes == -1:
        return False

    is_reparse_point = (file_attributes & 0x400) != 0
    is_directory = (file_attributes & 0x10) != 0

    return is_reparse_point and is_directory
