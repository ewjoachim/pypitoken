from __future__ import annotations


class PyPITokenException(Exception):
    """
    The base exception for all exceptions raised
    from this library. Any code raising a different
    exception would be considered a bug.
    """


class InvalidRestriction(PyPITokenException, ValueError):
    """
    Exception encountered while calling `Token.restrict`, due to unexpected
    parameters.
    """


class LoaderError(PyPITokenException):
    """
    Exception encountered while calling `Token.load`, due to unexpected
    format.

    Exception should be associated with a message in English that can be shown to the
    bearer to explain the error.
    """


class ValidationError(PyPITokenException):
    """
    Exception encountered while calling `Token.check`, the token should
    be considered invalid.

    Exception should be associated with a message in English that can be shown to the
    bearer to explain the error.
    """


class MissingContextError(ValidationError):
    """
    Exception encountered while calling `Token.check`, the token should
    be considered invalid.

    The restriction couldn't be checked because the context is missing required
    values
    """
