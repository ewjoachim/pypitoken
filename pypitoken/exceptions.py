class PyPITokenException(Exception):
    """
    The base exception for all exceptions raised
    from this library. Any code raising a different
    exception would be considered a bug.
    """


class LoadError(PyPITokenException):
    """
    Exception encoutered while calling `Token.load`, due to unexpected
    format.
    """


class ValidationError(PyPITokenException):
    """
    Exception encoutered while calling `Token.check`, the token should
    be considered invalid.
    """
