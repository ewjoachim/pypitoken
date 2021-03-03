import pymacaroons
import pytest

from pypitoken import exceptions, token


def test__Restriction__dump():
    class MyRestriction(token.Restriction):
        def dump_value(self):
            return {"a": ["b"]}

    assert MyRestriction().dump() == '{"a": ["b"]}'


def test__Restriction__validate_value__pass():
    class MyRestriction(token.Restriction):
        @staticmethod
        def get_schema():
            return {
                "type": "object",
                "properties": {
                    "version": {"type": "integer", "const": 42},
                },
                "required": ["version"],
            }

    assert MyRestriction().validate_value({"version": 42}) is None


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
def test__Restriction__validate_value__fail(value):
    class MyRestriction(token.Restriction):
        @staticmethod
        def get_schema():
            return {
                "type": "object",
                "properties": {
                    "version": {"type": "integer", "const": 42},
                },
                "required": ["version"],
            }

    with pytest.raises(exceptions.ValidationError):
        MyRestriction().validate_value(value)


def test__NoopRestriction__validate_value__pass():
    assert (
        token.NoopRestriction.validate_value(
            value={"version": 1, "permissions": "user"}
        )
        is None
    )


@pytest.mark.parametrize(
    "value",
    [
        {"permissions": "user"},
        {"version": 2, "permissions": "user"},
        {"version": 1},
        {"version": 1, "permissions": {"projects": ["a"]}},
        {"version": 1, "permissions": "something else"},
    ],
)
def test__NoopRestriction__validate_value__fail(value):
    with pytest.raises(exceptions.ValidationError):
        token.NoopRestriction.validate_value(value=value)


def test__NoopRestriction__load_from_value():
    noop = token.NoopRestriction.load_from_value(value={})
    assert noop == token.NoopRestriction()


def test__NoopRestriction__check():
    noop = token.NoopRestriction()
    assert noop.check(context={}) is None


def test__NoopRestriction__dump_value():
    noop = token.NoopRestriction()
    assert noop.dump_value() == {"version": 1, "permissions": "user"}


@pytest.mark.parametrize(
    "value",
    [
        {"version": 1, "permissions": {"projects": []}},
        {"version": 1, "permissions": {"projects": ["a"]}},
        {"version": 1, "permissions": {"projects": ["a", "b"]}},
    ],
)
def test__ProjectsRestriction__validate_value__pass(value):
    assert token.ProjectsRestriction.validate_value(value=value) is None


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
    ],
)
def test__ProjectsRestriction__validate_value__fail(value):
    with pytest.raises(exceptions.ValidationError):
        token.ProjectsRestriction.validate_value(value=value)


def test__ProjectsRestriction__load_from_value():
    value = {"version": 1, "permissions": {"projects": ["a", "b"]}}
    restriction = token.ProjectsRestriction.load_from_value(value=value)
    assert restriction == token.ProjectsRestriction(projects=["a", "b"])


def test__ProjectsRestriction__check__pass():
    restriction = token.ProjectsRestriction(projects=["a", "b"])
    assert restriction.check(context={"project": "a"}) is None


def test__ProjectsRestriction__check__fail_project():
    restriction = token.ProjectsRestriction(projects=["a", "b"])
    with pytest.raises(exceptions.ValidationError):
        restriction.check(context={"project": "c"})


def test__ProjectsRestriction__check__fail_context():
    restriction = token.ProjectsRestriction(projects=["a", "b"])
    with pytest.raises(exceptions.MissingContextError):
        restriction.check(context={})


def test__ProjectsRestriction__dump_value():
    restriction = token.ProjectsRestriction(projects=["a", "b"])
    assert restriction.dump_value() == {
        "version": 1,
        "permissions": {"projects": ["a", "b"]},
    }


def test__RESTRICTION_CLASSES():
    # This test ensures we didn't forget to add new restriction classes to
    # the set.
    assert set(token.RESTRICTION_CLASSES) == {
        cls
        for cls in token.Restriction.__subclasses__()
        if cls.__module__ == "pypitoken.token"
    }


def test__json_load_caveat__pass():
    assert token.json_load_caveat('{"a": "b"}') == {"a": "b"}


@pytest.mark.parametrize(
    "caveat, error",
    [
        (
            '{"a": "b"',
            "Error while loading caveat: Expecting ',' delimiter: line 1 column 10 (char 9)",
        ),
        ("[1, 2, 3]", "Caveat is a well-formed JSON string but not a dict: [1, 2, 3]"),
    ],
)
def test__json_load_caveat__fail(caveat, error):
    with pytest.raises(exceptions.LoadError) as exc_info:
        token.json_load_caveat(caveat=caveat)
    assert str(exc_info.value) == error


@pytest.mark.parametrize(
    "caveat, output",
    [
        (
            '{"version": 1, "permissions": "user"}',
            token.NoopRestriction(),
        ),
        (
            '{"version": 1, "permissions": {"projects": ["a", "b"]}}',
            token.ProjectsRestriction(projects=["a", "b"]),
        ),
    ],
)
def test__load_restriction__pass(caveat, output):
    assert token.load_restriction(caveat=caveat) == output


@pytest.mark.parametrize(
    "caveat, error",
    [
        (
            "{",
            "Error while loading caveat: Expecting property name enclosed in double quotes: line 1 column 2 (char 1)",
        ),
        (
            '{"version": 1, "permissions": "something"}',
            "Could not find matching Restriction for {'version': 1, 'permissions': 'something'}",
        ),
    ],
)
def test__load_restriction__fail(caveat, error):
    with pytest.raises(exceptions.LoadError) as exc_info:
        token.load_restriction(caveat=caveat)
    assert str(exc_info.value) == error


def test__check_caveat__pass():
    value = token.check_caveat(
        caveat='{"version": 1, "permissions": {"projects": ["a", "b"]}}',
        context={"project": "a"},
    )
    assert value is True


def test__check_caveat__fail_load():
    value = token.check_caveat("{", context={})
    assert value is False


def test__check_caveat__fail_check():
    value = token.check_caveat(
        '{"version": 1, "permissions": {"projects": ["a", "b"]}}',
        context={"project": "c"},
    )
    assert value is False


def test__check_caveat__fail_context():
    value = token.check_caveat(
        '{"version": 1, "permissions": {"projects": ["a", "b"]}}', context={}
    )
    assert value is False


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


def test__Token__load__fail_prefix():

    with pytest.raises(exceptions.LoadError) as exc_info:
        token.Token.load("foobar")

    assert str(exc_info.value) == "Token is missing a prefix"


def test__Token__load__fail_format():

    with pytest.raises(exceptions.LoadError) as exc_info:
        token.Token.load("foobar-baz")

    error = (
        "Deserialization error: cannot determine data format of binary-encoded macaroon"
    )
    assert str(exc_info.value) == error


def test__Token__create():

    tok = token.Token.create(
        domain="example.com",
        identifier="123foo",
        key="ohsosecret",
        prefix="pre",
    )
    raw = "pre-AgELZXhhbXBsZS5jb20CBjEyM2ZvbwAABiCK4TytWvy17_Up7TvhdVDhFx8cjU_ne_6wtOqxPUZmxw"
    assert tok.dump() == raw


def test__Token__derive__empty(create_token):

    tok = create_token()
    assert tok._macaroon.caveats == []
    tok.derive()
    caveats = [c._caveat_id.decode("utf-8") for c in tok._macaroon.caveats]
    assert caveats == ['{"version": 1, "permissions": "user"}']


def test__Token__derive__projects(create_token):

    tok = create_token()
    assert tok._macaroon.caveats == []
    tok.derive(projects=["a", "b"])
    caveats = [c._caveat_id.decode("utf-8") for c in tok._macaroon.caveats]
    assert caveats == ['{"version": 1, "permissions": {"projects": ["a", "b"]}}']


def test__Token__derive__multiple(create_token):

    tok = create_token()
    assert tok._macaroon.caveats == []
    tok.derive()
    tok.derive(projects=["a", "b"])
    tok.derive(projects=["a", "d"])
    caveats = [c._caveat_id.decode("utf-8") for c in tok._macaroon.caveats]
    assert caveats == [
        '{"version": 1, "permissions": "user"}',
        '{"version": 1, "permissions": {"projects": ["a", "b"]}}',
        '{"version": 1, "permissions": {"projects": ["a", "d"]}}',
    ]


def test__Token__check__pass(create_token):

    tok = create_token(key="ohsosecret")
    tok.derive(projects=["a", "b"])
    tok.check(key="ohsosecret", project="a")


def test__Token__check__fail__signature(create_token):

    tok = create_token(key="ohsosecret")
    tok.derive(projects=["a", "b"])
    with pytest.raises(exceptions.ValidationError):
        tok.check(key="notthatsecret", project="a")


def test__Token__check__fail__caveat(create_token):

    tok = create_token(key="ohsosecret")
    tok.derive(projects=["a", "b"])
    with pytest.raises(exceptions.ValidationError):
        tok.check(key="ohsosecret", project="c")


def test__Token__restrictions(create_token):

    tok = create_token()
    tok.derive()
    tok.derive(projects=["a", "b"])
    tok.derive(projects=["a", "d"])
    assert tok.restrictions == [
        token.NoopRestriction(),
        token.ProjectsRestriction(projects=["a", "b"]),
        token.ProjectsRestriction(projects=["a", "d"]),
    ]
