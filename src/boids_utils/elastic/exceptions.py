"""
Exceptions raised by the elastic module
"""

class DocumentNotFoundError(RuntimeError):
    """ Raised when an attempt to access a non-existant document is made. """

class MultipleDocumentsFoundError(RuntimeError):
    """ Raised when a search expects exactly one document, but yields more than one. """

class ConfigurationError(RuntimeError):
    """ Raised when an expected/required configuration property is not provided. """
