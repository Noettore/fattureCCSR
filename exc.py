"""Define Python user-defined exceptions"""

class FattureSanRossoreError(Exception):
    """Base class for other exceptions"""


class FileError(FattureSanRossoreError):
    """Basic exception for errors raised by files"""
    def __init__(self, file_path, msg=None):
        if msg is None:
            msg = "An error occurred with file %s" % file_path
        super(FileError, self).__init__(msg)
        self.file_path = file_path

class NoFileExtensionError(FileError):
    """Raised when a file has no exception"""
    def __init__(self, file_path):
        super(NoFileExtensionError, self).__init__(file_path, msg="File %s has no extension!" % file_path)
class WrongFileExtensionError(FileError):
    """Raised when a file extension is not accepted"""
    def __init__(self, file_path, file_ext, allowed_ext):
        super(WrongFileExtensionError, self).__init__(file_path, msg="Cannot accept file %s extension %s. Allowed extensions are %s" % (file_path, file_ext, allowed_ext))
        self.file_ext = file_ext

class NoFileError(FileError):
    """Raised when file_path is None or an empty string"""
    def __init__(self):
        super(NoFileError, self).__init__(None, msg="Not setted or empty file path!")


class ActionError(FattureSanRossoreError):
    """Basic exception for errors raised by actions"""
    def __init__(self, action, msg=None):
        if msg is None:
            msg = "An error occurred with %s action" % action
        super(ActionError, self).__init__(msg)
        self.action = action

class InvalidActionError(ActionError):
    """Raised when an invalid action is used"""
    def __init__(self, action):
        super(InvalidActionError, self).__init__(action, "Invalid action %s" % action)
