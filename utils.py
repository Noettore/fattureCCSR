"""Some useful utilities"""

import os

import exc

def file_extension(file_path: str, allowed_ext: set = None) -> str:
    """Return the file extension if that's in the allowed extension set"""
    if file_path in (None, ""):
        raise exc.NoFileError()
    file_ext = os.path.splitext(file_path)[1]
    if file_ext in (None, ""):
        raise exc.NoFileExtensionError
    if allowed_ext is not None and file_ext not in allowed_ext:
        raise exc.WrongFileExtensionError
    return file_ext
