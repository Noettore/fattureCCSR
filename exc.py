"""Define Python user-defined exceptions"""

class Error(Exception):
    """Base class for other exceptions"""

class WrongFileExtension(Error):
    """Raised when a file extension is not accepted"""
