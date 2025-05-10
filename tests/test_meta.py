# Some parts of pypitoken have redundant code that can't easily be factored
# (for example, some high-level functions need to expose the same parameters
# as lower level functions). In those case, using *args/**kwargs would ensure
# we don't have code duplication, but at the price of our function signatures
# being much worse. The alternative, done here, is to duplicate the parts that
# need to be duplicated, but write tests to ensure the duplicated parts stay
# synchronised through time.
# When adding new restriction, there are a number of small things we may forget
# and those tests do their best to double check every one of them.
from __future__ import annotations

import inspect

from pypitoken import restrictions, token


def test__Restriction__get_subclasses():
    # This test ensures we didn't forget to add new restriction classes to
    # the set.
    assert set(restrictions.Restriction._get_subclasses()) == {
        cls
        for cls in restrictions.Restriction.__subclasses__()
        if cls.__module__ == "pypitoken.restrictions"
    }


def test_Token__restrict__signature():
    # Token.restrict() signature must match the combined signature of all
    # Restriction subclasses from_parameters methods
    restrict_parameters = dict(inspect.signature(token.Token.restrict).parameters)
    restrict_parameters.pop("self")

    all_params = set()
    for subclass in restrictions.Restriction._get_subclasses():
        restriction_params = dict(
            inspect.signature(subclass.from_parameters).parameters
        )
        params = {p for p in restriction_params.values() if not p.kind == p.VAR_KEYWORD}
        assert not params & all_params
        all_params |= params

    assert all_params == set(restrict_parameters.values())


def test_Token__check__signature():
    # Token.check signature must match Context's constructor (except the key)
    check_parameters = dict(inspect.signature(token.Token.check).parameters)
    check_parameters.pop("self")
    check_parameters.pop("key")
    context_parameters = dict(inspect.signature(restrictions.Context).parameters)

    assert check_parameters == context_parameters


def test__Token__restrict_all_restriction_types(create_token):
    # This specific test verifies that we haven't forgotten to pass an argument
    # to restrictions_from_parameters() inside restrict()
    key = "ohsosecret"
    tok = create_token(key=key)
    tok.restrict(
        not_before=1_234_567_890,
        not_after=1_234_567_892,
        project_names=["a", "b"],
        project_ids=[
            "00000000-0000-0000-0000-000000000000",
            "00000000-0000-0000-0000-000000000001",
        ],
        user_id="00000000-0000-0000-0000-000000000003",
        legacy_not_before=1_234_567_890,
        legacy_not_after=1_234_567_892,
        legacy_project_names=["a", "b"],
        legacy_noop=True,
    )
    restriction_types = {type(r) for r in tok.restrictions}
    assert restriction_types == set(restrictions.Restriction._get_subclasses())


def test__Token__check_all_restriction_types(create_token, mocker):
    # This specific test verifies that we haven't forgotten to pass an argument
    # to Context() inside check()
    # I hate mocks too, but I don't think we have a choice here.

    key = "ohsosecret"
    tok = create_token(key=key)
    real_context = restrictions.Context
    context_mock = mocker.patch("pypitoken.restrictions.Context")
    tok.check(
        key=key,
        project_name="a",
        project_id="aaaa",
        now=1_234_567_891,
        user_id="uuuu",
    )
    args, kwargs = context_mock.call_args
    assert not args
    assert set(kwargs) == set(inspect.signature(real_context).parameters)
