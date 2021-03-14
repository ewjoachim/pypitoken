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


class MissingContextError(ValidationError, NotImplementedError):
    """
    Token check failed du to missing information in the passed context.

    The token should be considered invalid, but this is likely a problem in the
    implementing code: we most likely forgot a context element.

    Due to PyMacaroons & this lib implementation details, this exception is currently
    not fired by `Token.check`.
    """
