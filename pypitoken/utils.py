import inspect
from typing import Callable, List


def merge_parameters(*callables: Callable) -> List[inspect.Parameter]:
    """
    Return a list of Parameters object matching every parameters from input callables.
    """
    return [
        param
        for func in callables
        for _, param in inspect.signature(func).parameters.items()
        if param.kind != inspect.Parameter.VAR_KEYWORD
    ]


def replace_signature(method: Callable, parameters: List[inspect.Parameter]) -> None:
    """
    On the received method, keep the self parameter. Replace the other parameters
    with the list reciend in ``parameters``.

    Currently only supports methods.
    """
    signature = inspect.signature(method)
    method.__signature__ = inspect.signature(method).replace(  # type: ignore
        parameters=[signature.parameters["self"]] + parameters
    )
