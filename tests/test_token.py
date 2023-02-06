from __future__ import annotations

import pytest

from pypitoken import exceptions, restrictions, token


def test__Token__check_caveat__pass():
    errors = []
    value = token.Token._check_caveat(
        caveat='{"version": 1, "permissions": {"projects": ["a", "b"]}}',
        context=restrictions.Context(project_name="a"),
        errors=errors,
    )
    assert value is True
    assert errors == []


def test__check_caveat__fail_load_json():
    errors = []
    value = token.Token._check_caveat(
        "{", context=restrictions.Context(project_name="a"), errors=errors
    )
    assert value is False
    messages = [str(e) for e in errors]
    assert messages == [
        "Error while loading caveat: "
        "Expecting property name enclosed in double quotes: "
        "line 1 column 2 (char 1)"
    ]


def test__check_caveat__fail_load():
    errors = []
    value = token.Token._check_caveat(
        '{"version": 13}', context=restrictions.Context(project_name="a"), errors=errors
    )
    assert value is False
    messages = [str(e) for e in errors]
    assert messages == ["Could not find matching Restriction for {'version': 13}"]


def test__check_caveat__fail_check():
    errors = []

    value = token.Token._check_caveat(
        '{"version": 1, "permissions": {"projects": ["a", "b"]}}',
        context=restrictions.Context(project_name="c"),
        errors=errors,
    )
    assert value is False
    messages = [str(e) for e in errors]
    assert messages == ["This token can only be used for project(s): a, b. Received: c"]


def test__Token__init(create_macaroon):
    mac = create_macaroon()
    tok = token.Token("yay", mac)
    assert tok.prefix == "yay"
    assert tok._macaroon == mac


def test__Token__domain(create_macaroon):
    assert (
        token.Token("yay", create_macaroon(location="somewhere")).domain == "somewhere"
    )


def test__Token__identifier(create_macaroon):
    assert token.Token("yay", create_macaroon(identifier="foo")).identifier == "foo"


def test__Token__load__pass():
    raw = "pre-AgELZXhhbXBsZS5jb20CBjEyM2ZvbwAABiCK4TytWvy17_Up7TvhdVDhFx8cjU_ne_6wtOqxPUZmxw"
    tok = token.Token.load(raw)
    assert tok.domain == "example.com"
    assert tok.identifier == "123foo"


@pytest.mark.parametrize(
    "raw, error",
    [
        ("foobar", "Token is missing a prefix"),
        (
            "foobar-baz",
            "Deserialization error: cannot determine data format of binary-encoded macaroon",
        ),
        (
            "pypi-AgEIcHlwaS5vcmcCAWEAAAYgNh9pJUqVF-EtMCwGaZYcStFR07Rb",
            "Deserialization error: field data extends past end of buffer",
        ),
    ],
)
def test__Token__load__fail_format(raw, error):
    with pytest.raises(exceptions.LoaderError) as exc_info:
        token.Token.load(raw=raw)

    assert str(exc_info.value) == error


@pytest.mark.parametrize("key", ["ohsosecret", b"ohsosecret"])
def test__Token__create(key):
    tok = token.Token.create(
        domain="example.com",
        identifier="123foo",
        key=key,
        prefix="pre",
    )
    raw = "pre-AgELZXhhbXBsZS5jb20CBjEyM2ZvbwAABiCK4TytWvy17_Up7TvhdVDhFx8cjU_ne_6wtOqxPUZmxw"
    assert tok.dump() == raw


def test__Token__restrict__empty(create_token):
    tok = create_token()
    assert tok._macaroon.caveats == []
    tok.restrict()
    caveats = [c._caveat_id.decode("utf-8") for c in tok._macaroon.caveats]
    assert caveats == []


def test__Token__restrict__projects(create_token):
    tok = create_token()
    assert tok._macaroon.caveats == []
    tok.restrict(legacy_project_names=["a", "b"])
    caveats = [c._caveat_id.decode("utf-8") for c in tok._macaroon.caveats]
    assert caveats == ['{"version": 1, "permissions": {"projects": ["a", "b"]}}']


def test__Token__restrict__multiple(create_token):
    tok = create_token()
    assert tok._macaroon.caveats == []
    tok.restrict(project_names=["a", "b"])
    tok.restrict(legacy_project_names=["a", "d"])
    caveats = [c._caveat_id.decode("utf-8") for c in tok._macaroon.caveats]
    assert caveats == [
        '[1, ["a", "b"]]',
        '{"version": 1, "permissions": {"projects": ["a", "d"]}}',
    ]


def test__Token__check__pass(create_token):
    key = "ohsosecret"
    tok = create_token(key=key)
    tok.restrict(project_names=["a", "b"])
    tok.check(key=key, project_name="a", now=1_234_567_890)


def test__Token__check__fail__signature(create_token):
    tok = create_token(key="ohsosecret")
    tok.restrict(project_names=["a", "b"])
    with pytest.raises(exceptions.ValidationError) as exc_info:
        tok.check(key="notthatsecret", project_name="a")
    assert (
        str(exc_info.value) == "Error while validating token: Signatures do not match"
    )


def test__Token__check__fail__caveat(create_token):
    tok = create_token(key="ohsosecret")
    tok.restrict(project_names=["a", "b"])
    with pytest.raises(exceptions.ValidationError) as exc_info:
        tok.check(key="ohsosecret", project_name="c")
    assert (
        str(exc_info.value)
        == "Error while validating token: This token can only be used for project(s): a, b. Received: c"
    )


def test__Token__restrictions(create_token):
    tok = create_token()
    tok.restrict(project_names=["a", "b"])
    tok.restrict(project_names=["a", "d"])
    assert tok.restrictions == [
        restrictions.ProjectNamesRestriction(project_names=["a", "b"]),
        restrictions.ProjectNamesRestriction(project_names=["a", "d"]),
    ]
