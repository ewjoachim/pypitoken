from __future__ import annotations

import inspect

from pypitoken import utils


def test__merge_parameters():
    def a(b: int) -> str:
        pass

    def c(*, d: float) -> None:
        pass

    result = utils.merge_parameters(a, c)

    assert result == [
        inspect.Parameter(
            "b", kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=int
        ),
        inspect.Parameter("d", kind=inspect.Parameter.KEYWORD_ONLY, annotation=float),
    ]


def test__replace_signature():
    def a(b: int) -> str:
        pass

    def c(*, d: float, **kwargs) -> None:
        pass

    class E:
        def f(self, **kwargs) -> int:  # Input
            pass

        def g(self, b: int, *, d: float) -> int:  # What we expect
            pass

    utils.replace_signature(E.f, utils.merge_parameters(a, c))

    assert inspect.Signature.from_callable(E.f) == inspect.Signature.from_callable(E.g)
