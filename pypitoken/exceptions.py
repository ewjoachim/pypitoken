class PyPITokenException(Exception):
    pass


class LoadError(PyPITokenException):
    pass


class ValidationError(PyPITokenException):
    pass


class MissingContextError(ValidationError, NotImplementedError):
    pass
