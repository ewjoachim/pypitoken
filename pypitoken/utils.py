from __future__ import annotations

import inspect
from typing import Callable


def merge_parameters(*callables: Callable) -> list[inspect.Parameter]:
    """
    Return a list of Parameters object matching every parameters from input callables.
    """
    return [
        param
        for func in callables
        for _, param in inspect.signature(func).parameters.items()
        if param.kind != inspect.Parameter.VAR_KEYWORD
    ]


def replace_signature(method: Callable, parameters: list[inspect.Parameter]) -> None:
    """
    On the received method, keep the self parameter. Replace the other parameters
    with the list received in ``parameters``.

    Currently only supports methods.
    """
    signature = inspect.signature(method)
    method.__signature__ = inspect.signature(method).replace(  # type: ignore
        parameters=[signature.parameters["self"]] + parameters
    )
