from __future__ import annotations

import dataclasses
import datetime
import inspect

import pymacaroons
import pytest

from pypitoken import exceptions, token


def test__Restriction__dump_json():
    class MyRestriction(token.Restriction):
        def dump(self):
            return {"a": ["b"]}

    assert MyRestriction().dump_json() == '{"a": ["b"]}'


def test__Restriction__load_value__pass():
    @dataclasses.dataclass
    class MyRestriction(token.Restriction):
        version: int

        @staticmethod
        def _get_schema():
            return {
                "type": "object",
                "properties": {
                    "version": {"type": "integer", "const": 42},
                },
                "required": ["version"],
            }

        @classmethod
        def _extract_kwargs(cls, value):
            return {"version": value["version"]}

    assert MyRestriction._load_value(value={"version": 42}).version == 42


@pytest.mark.parametrize(
    "value",
    [
        [],
        {},
        {"some": "key"},
        {"version": "42"},
        {"version": 17},
    ],
)
def test__Restriction__load_value__fail(value):
    class MyRestriction(token.Restriction):
        @staticmethod
        def _get_schema():
            return {
                "type": "object",
                "properties": {
                    "version": {"type": "integer", "const": 42},
                },
                "required": ["version"],
            }

    with pytest.raises(exceptions.LoaderError):
        MyRestriction._load_value(value=value)


def test__LegacyNoopRestriction__load_value__pass():
    tok = token.LegacyNoopRestriction._load_value(
        value={"version": 1, "permissions": "user"}
    )
    assert tok == token.LegacyNoopRestriction()


@pytest.mark.parametrize(
    "value",
    [
        {"permissions": "user"},
        {"version": 2, "permissions": "user"},
        {"version": 1},
        {"version": 1, "permissions": {"projects": ["a"]}},
        {"version": 1, "permissions": "something else"},
        {"version": 1, "permissions": "user", "additional": "key"},
    ],
)
def test__LegacyNoopRestriction__load_value__fail(value):
    with pytest.raises(exceptions.LoaderError):
        token.LegacyNoopRestriction._load_value(value=value)


def test__LegacyNoopRestriction__extract_kwargs():
    noop = token.LegacyNoopRestriction._extract_kwargs(value={"any": "content"})
    assert noop == {}


def test__LegacyNoopRestriction__check():
    noop = token.LegacyNoopRestriction()
    assert noop.check(context=token.Context(project="foo")) is None


def test__LegacyNoopRestriction__dump():
    noop = token.LegacyNoopRestriction()
    assert noop.dump() == {"version": 1, "permissions": "user"}


def test__LegacyNoopRestriction__from_parameters__empty():
    assert (
        token.LegacyNoopRestriction.from_parameters() == token.LegacyNoopRestriction()
    )


def test__LegacyNoopRestriction__from_parameters__not_empty():
    assert token.LegacyNoopRestriction.from_parameters(a=1) is None


@pytest.mark.parametrize(
    "value, restriction",
    [
        (
            {"version": 1, "permissions": {"projects": []}},
            token.LegacyProjectsRestriction(projects=[]),
        ),
        (
            {"version": 1, "permissions": {"projects": ["a"]}},
            token.LegacyProjectsRestriction(projects=["a"]),
        ),
        (
            {"version": 1, "permissions": {"projects": ["a", "b"]}},
            token.LegacyProjectsRestriction(projects=["a", "b"]),
        ),
    ],
)
def test__LegacyProjectsRestriction__load_value__pass(value, restriction):
    assert token.LegacyProjectsRestriction._load_value(value=value) == restriction


@pytest.mark.parametrize(
    "value",
    [
        {"permissions": {"projects": ["a"]}},
        {"version": 2, "permissions": {"projects": ["a"]}},
        {"version": 1},
        {"version": 1, "permissions": "user"},
        {"version": 1, "permissions": {"a": "b"}},
        {"version": 1, "permissions": {"projects": "a"}},
        {"version": 1, "permissions": {"projects": [1]}},
        {"version": 1, "permissions": {"projects": ["a", 1]}},
        {"version": 1, "permissions": {"projects": ["a"]}, "additional": "key"},
        {"version": 1, "permissions": {"projects": ["a"], "additional": "key"}},
    ],
)
def test__LegacyProjectsRestriction__load_value__fail(value):
    with pytest.raises(exceptions.LoaderError):
        token.LegacyProjectsRestriction._load_value(value=value)


def test__LegacyProjectsRestriction__extract_kwargs():
    value = {"version": 1, "permissions": {"projects": ["a", "b"]}}
    kwargs = token.LegacyProjectsRestriction._extract_kwargs(value=value)
    assert kwargs == {"projects": ["a", "b"]}


def test__LegacyProjectsRestriction__check__pass():
    restriction = token.LegacyProjectsRestriction(projects=["a", "b"])
    assert restriction.check(context=token.Context(project="a")) is None


def test__LegacyProjectsRestriction__check__fail():
    restriction = token.LegacyProjectsRestriction(projects=["a", "b"])
    with pytest.raises(exceptions.ValidationError):
        restriction.check(context=token.Context(project="c"))


def test__LegacyProjectsRestriction__dump():
    restriction = token.LegacyProjectsRestriction(projects=["a", "b"])
    assert restriction.dump() == {
        "version": 1,
        "permissions": {"projects": ["a", "b"]},
    }


def test__LegacyProjectsRestriction__from_parameters__empty():
    assert token.LegacyProjectsRestriction.from_parameters() is None


def test__LegacyProjectsRestriction__from_parameters__not_empty():
    assert token.LegacyProjectsRestriction.from_parameters(
        projects=["a", "b"]
    ) == token.LegacyProjectsRestriction(projects=["a", "b"])


def test__LegacyDateRestriction__load_value__pass():
    assert token.LegacyDateRestriction._load_value(
        value={"nbf": 1_234_567_890, "exp": 1_234_567_900}
    ) == token.LegacyDateRestriction(not_before=1_234_567_890, not_after=1_234_567_900)


@pytest.mark.parametrize(
    "value",
    [
        {},
        {"nbf": "2000-01-01 00:00:00", "exp": "2100-01-01 00:00:00"},
        {"nbf": "1_234_567_890", "exp": "1_234_567_900"},
        {"nbf": 1_234_567_890},
        {"exp": 1_234_567_890},
    ],
)
def test__LegacyDateRestriction__load_value__fail(value):
    with pytest.raises(exceptions.LoaderError):
        token.LegacyDateRestriction._load_value(value=value)


def test__LegacyDateRestriction__extract_kwargs():
    value = {"nbf": 1_234_567_890, "exp": 1_234_567_900}
    kwargs = token.LegacyDateRestriction._extract_kwargs(value=value)
    assert kwargs == {"not_before": 1_234_567_890, "not_after": 1_234_567_900}


def test__LegacyDateRestriction__check__pass():
    restriction = token.LegacyDateRestriction._load_value(
        value={"nbf": 1_234_567_890, "exp": 1_234_567_900}
    )
    assert (
        restriction.check(context=token.Context(project="a", now=1_234_567_895)) is None
    )


@pytest.mark.parametrize(
    "value",
    [
        1_234_567_000,
        1_234_568_000,
    ],
)
def test__LegacyDateRestriction__check__fail(value):
    restriction = token.LegacyDateRestriction._load_value(
        value={"nbf": 1_234_567_890, "exp": 1_234_567_900}
    )
    with pytest.raises(exceptions.ValidationError):
        restriction.check(context=token.Context(project="a", now=value))


def test__LegacyDateRestriction__dump():
    restriction = token.LegacyDateRestriction._load_value(
        value={"nbf": 1_234_567_890, "exp": 1_234_567_900}
    )
    assert restriction.dump() == {
        "nbf": 1_234_567_890,
        "exp": 1_234_567_900,
    }


def test__LegacyDateRestriction__from_parameters__empty():
    assert token.LegacyDateRestriction.from_parameters() is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"not_before": 1_234_567_890},
        {"not_after": 1_234_567_900},
        {
            "not_before": datetime.datetime(2000, 1, 1),
            "not_after": datetime.datetime(2100, 1, 1),
        },
    ],
)
def test__LegacyDateRestriction__from_parameters__fail(kwargs):
    with pytest.raises(exceptions.InvalidRestriction):
        assert token.LegacyDateRestriction.from_parameters(**kwargs) is None


@pytest.mark.parametrize(
    "kwargs, expected",
    [
        (
            {"not_before": 1_234_567_890, "not_after": 1_234_567_900},
            token.LegacyDateRestriction._load_value(
                value={"nbf": 1_234_567_890, "exp": 1_234_567_900}
            ),
        ),
        (
            {
                "not_before": datetime.datetime(
                    2000, 1, 1, tzinfo=datetime.timezone.utc
                ),
                "not_after": datetime.datetime(
                    2100, 1, 1, tzinfo=datetime.timezone.utc
                ),
            },
            token.LegacyDateRestriction._load_value(
                value={"nbf": 946_684_800, "exp": 4_102_444_800}
            ),
        ),
    ],
)
def test__LegacyDateRestriction__from_parameters__ok(kwargs, expected):
    assert token.LegacyDateRestriction.from_parameters(**kwargs) == expected


def test__Restriction__get_subclasses():
    # This test ensures we didn't forget to add new restriction classes to
    # the set.
    assert set(token.Restriction._get_subclasses()) == {
        cls
        for cls in token.Restriction.__subclasses__()
        if cls.__module__ == "pypitoken.token"
    }


def test__Restriction__json_load_caveat__pass():
    assert token.Restriction._json_load_caveat('{"a": "b"}') == {"a": "b"}


def test__Restriction__json_load_caveat__fail():
    with pytest.raises(exceptions.LoaderError) as exc_info:
        token.Restriction._json_load_caveat(caveat='{"a": "b"')
    assert (
        str(exc_info.value) == "Error while loading caveat: "
        "Expecting ',' delimiter: line 1 column 10 (char 9)"
    )


@pytest.mark.parametrize(
    "caveat, output",
    [
        (
            {"version": 1, "permissions": "user"},
            token.LegacyNoopRestriction(),
        ),
        (
            {"version": 1, "permissions": {"projects": ["a", "b"]}},
            token.LegacyProjectsRestriction(projects=["a", "b"]),
        ),
    ],
)
def test__Restriction__load__pass(caveat, output):
    assert token.Restriction.load(caveat=caveat) == output


def test__Restriction__load__fail():
    with pytest.raises(exceptions.LoaderError) as exc_info:
        token.Restriction.load(caveat={"version": 1, "permissions": "something"})
    assert (
        str(exc_info.value)
        == "Could not find matching Restriction for {'version': 1, 'permissions': 'something'}"
    )


def test__Restriction__load_json():
    restriction = token.Restriction.load_json(
        caveat='{"version": 1, "permissions": "user"}'
    )
    assert restriction == token.LegacyNoopRestriction()


def test__Restriction__restrictions_from_parameters():
    restrictions = list(
        token.Restriction.restrictions_from_parameters(
            projects=["a", "b"], not_before=1, not_after=5
        )
    )
    assert restrictions == [
        token.LegacyProjectsRestriction(projects=["a", "b"]),
        token.LegacyDateRestriction(not_before=1, not_after=5),
    ]


def test__Token__check_caveat__pass():
    errors = []
    value = token.Token._check_caveat(
        caveat='{"version": 1, "permissions": {"projects": ["a", "b"]}}',
        context=token.Context(project="a"),
        errors=errors,
    )
    assert value is True
    assert errors == []


def test__check_caveat__fail_load_json():
    errors = []
    value = token.Token._check_caveat(
        "{", context=token.Context(project="a"), errors=errors
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
        '{"version": 13}', context=token.Context(project="a"), errors=errors
    )
    assert value is False
    messages = [str(e) for e in errors]
    assert messages == ["Could not find matching Restriction for {'version': 13}"]


def test__check_caveat__fail_check():
    errors = []

    value = token.Token._check_caveat(
        '{"version": 1, "permissions": {"projects": ["a", "b"]}}',
        context=token.Context(project="c"),
        errors=errors,
    )
    assert value is False
    messages = [str(e) for e in errors]
    assert messages == ["This token can only be used for project(s): a, b. Received: c"]


@pytest.fixture
def create_macaroon():
    def _(**kwargs):
        defaults = {
            "location": "example.com",
            "identifier": "123foo",
            "key": "ohsosecret",
            "version": pymacaroons.MACAROON_V2,
        }
        defaults.update(kwargs)
        return pymacaroons.Macaroon(**defaults)

    return _


@pytest.fixture
def create_token():
    def _(**kwargs):
        defaults = {
            "domain": "example.com",
            "identifier": "123foo",
            "key": "ohsosecret",
            "prefix": "pre",
        }
        defaults.update(kwargs)
        return token.Token.create(**defaults)

    return _


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
    assert caveats == ['{"version": 1, "permissions": "user"}']


def test__Token__restrict__projects(create_token):

    tok = create_token()
    assert tok._macaroon.caveats == []
    tok.restrict(projects=["a", "b"])
    caveats = [c._caveat_id.decode("utf-8") for c in tok._macaroon.caveats]
    assert caveats == ['{"version": 1, "permissions": {"projects": ["a", "b"]}}']


def test__Token__restrict__multiple(create_token):

    tok = create_token()
    assert tok._macaroon.caveats == []
    tok.restrict()
    tok.restrict(projects=["a", "b"])
    tok.restrict(projects=["a", "d"])
    caveats = [c._caveat_id.decode("utf-8") for c in tok._macaroon.caveats]
    assert caveats == [
        '{"version": 1, "permissions": "user"}',
        '{"version": 1, "permissions": {"projects": ["a", "b"]}}',
        '{"version": 1, "permissions": {"projects": ["a", "d"]}}',
    ]


@pytest.mark.parametrize("key", ["ohsosecret", b"ohsosecret"])
def test__Token__check__pass(create_token, key):

    tok = create_token(key=key)
    tok.restrict(projects=["a", "b"])
    tok.check(key=key, project="a", now=1_234_567_890)


def test__Token__check__pass__optional_now(create_token):

    tok = create_token(key="ohsosecret")
    tok.restrict(not_before=1_000_000_000, not_after=3_000_000_000)
    tok.check(key="ohsosecret", project="a")


def test__Token__check__fail__signature(create_token):

    tok = create_token(key="ohsosecret")
    tok.restrict(projects=["a", "b"])
    with pytest.raises(exceptions.ValidationError) as exc_info:
        tok.check(key="notthatsecret", project="a")
    assert (
        str(exc_info.value) == "Error while validating token: Signatures do not match"
    )


def test__Token__check__fail__caveat(create_token):

    tok = create_token(key="ohsosecret")
    tok.restrict(projects=["a", "b"])
    with pytest.raises(exceptions.ValidationError) as exc_info:
        tok.check(key="ohsosecret", project="c")
    assert (
        str(exc_info.value)
        == "Error while validating token: This token can only be used for project(s): a, b. Received: c"
    )


def test__Token__restrictions(create_token):

    tok = create_token()
    tok.restrict()
    tok.restrict(projects=["a", "b"])
    tok.restrict(projects=["a", "d"])
    assert tok.restrictions == [
        token.LegacyNoopRestriction(),
        token.LegacyProjectsRestriction(projects=["a", "b"]),
        token.LegacyProjectsRestriction(projects=["a", "d"]),
    ]


def test_Token__restrict__signature():
    assert (
        "projects" in inspect.Signature.from_callable(token.Token.restrict).parameters
    )
