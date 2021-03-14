class PyPITokenException(Exception):
    """
    The base exception for all exceptions raised
    from this library. Any code raising a different
    exception would be considered a bug.
    """


class LoaderError(PyPITokenException):
    """
    Exception encoutered while calling `Token.load`, due to unexpected
    format.

    Exception should be associated with a message in English that can be shown to the
    bearer to explain the error.
    """


class ValidationError(PyPITokenException):
    """
    Exception encoutered while calling `Token.check`, the token should
    be considered invalid.

    Exception should be associated with a message in English that can be shown to the
    bearer to explain the error.
    """
