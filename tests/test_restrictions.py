from __future__ import annotations

import dataclasses
import datetime

import pytest

from pypitoken import exceptions, restrictions


def test__Restriction__dump_json():
    class MyRestriction(restrictions.Restriction):
        def dump(self):
            return {"a": ["b"]}

    assert MyRestriction().dump_json() == '{"a": ["b"]}'


def test__Restriction__load_value__pass():
    @dataclasses.dataclass
    class MyRestriction(restrictions.Restriction):
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
    class MyRestriction(restrictions.Restriction):
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
    tok = restrictions.LegacyNoopRestriction._load_value(
        value={"version": 1, "permissions": "user"}
    )
    assert tok == restrictions.LegacyNoopRestriction()


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
        restrictions.LegacyNoopRestriction._load_value(value=value)


def test__LegacyNoopRestriction__extract_kwargs():
    noop = restrictions.LegacyNoopRestriction._extract_kwargs(value={"any": "content"})
    assert noop == {}


def test__LegacyNoopRestriction__check():
    noop = restrictions.LegacyNoopRestriction()
    assert noop.check(context=restrictions.Context(project="foo")) is None


def test__LegacyNoopRestriction__dump():
    noop = restrictions.LegacyNoopRestriction()
    assert noop.dump() == {"version": 1, "permissions": "user"}


def test__LegacyNoopRestriction__from_parameters__empty():
    assert (
        restrictions.LegacyNoopRestriction.from_parameters()
        == restrictions.LegacyNoopRestriction()
    )


def test__LegacyNoopRestriction__from_parameters__not_empty():
    assert restrictions.LegacyNoopRestriction.from_parameters(a=1) is None


@pytest.mark.parametrize(
    "value, restriction",
    [
        (
            {"version": 1, "permissions": {"projects": []}},
            restrictions.LegacyProjectsRestriction(projects=[]),
        ),
        (
            {"version": 1, "permissions": {"projects": ["a"]}},
            restrictions.LegacyProjectsRestriction(projects=["a"]),
        ),
        (
            {"version": 1, "permissions": {"projects": ["a", "b"]}},
            restrictions.LegacyProjectsRestriction(projects=["a", "b"]),
        ),
    ],
)
def test__LegacyProjectsRestriction__load_value__pass(value, restriction):
    assert (
        restrictions.LegacyProjectsRestriction._load_value(value=value) == restriction
    )


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
        restrictions.LegacyProjectsRestriction._load_value(value=value)


def test__LegacyProjectsRestriction__extract_kwargs():
    value = {"version": 1, "permissions": {"projects": ["a", "b"]}}
    kwargs = restrictions.LegacyProjectsRestriction._extract_kwargs(value=value)
    assert kwargs == {"projects": ["a", "b"]}


def test__LegacyProjectsRestriction__check__pass():
    restriction = restrictions.LegacyProjectsRestriction(projects=["a", "b"])
    assert restriction.check(context=restrictions.Context(project="a")) is None


def test__LegacyProjectsRestriction__check__fail():
    restriction = restrictions.LegacyProjectsRestriction(projects=["a", "b"])
    with pytest.raises(exceptions.ValidationError):
        restriction.check(context=restrictions.Context(project="c"))


def test__LegacyProjectsRestriction__dump():
    restriction = restrictions.LegacyProjectsRestriction(projects=["a", "b"])
    assert restriction.dump() == {
        "version": 1,
        "permissions": {"projects": ["a", "b"]},
    }


def test__LegacyProjectsRestriction__from_parameters__empty():
    assert restrictions.LegacyProjectsRestriction.from_parameters() is None


def test__LegacyProjectsRestriction__from_parameters__not_empty():
    assert restrictions.LegacyProjectsRestriction.from_parameters(
        projects=["a", "b"]
    ) == restrictions.LegacyProjectsRestriction(projects=["a", "b"])


def test__LegacyDateRestriction__load_value__pass():
    assert restrictions.LegacyDateRestriction._load_value(
        value={"nbf": 1_234_567_890, "exp": 1_234_567_900}
    ) == restrictions.LegacyDateRestriction(
        not_before=1_234_567_890, not_after=1_234_567_900
    )


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
        restrictions.LegacyDateRestriction._load_value(value=value)


def test__LegacyDateRestriction__extract_kwargs():
    value = {"nbf": 1_234_567_890, "exp": 1_234_567_900}
    kwargs = restrictions.LegacyDateRestriction._extract_kwargs(value=value)
    assert kwargs == {"not_before": 1_234_567_890, "not_after": 1_234_567_900}


def test__LegacyDateRestriction__check__pass():
    restriction = restrictions.LegacyDateRestriction._load_value(
        value={"nbf": 1_234_567_890, "exp": 1_234_567_900}
    )
    assert (
        restriction.check(context=restrictions.Context(project="a", now=1_234_567_895))
        is None
    )


@pytest.mark.parametrize(
    "value",
    [
        1_234_567_000,
        1_234_568_000,
    ],
)
def test__LegacyDateRestriction__check__fail(value):
    restriction = restrictions.LegacyDateRestriction._load_value(
        value={"nbf": 1_234_567_890, "exp": 1_234_567_900}
    )
    with pytest.raises(exceptions.ValidationError):
        restriction.check(context=restrictions.Context(project="a", now=value))


def test__LegacyDateRestriction__dump():
    restriction = restrictions.LegacyDateRestriction._load_value(
        value={"nbf": 1_234_567_890, "exp": 1_234_567_900}
    )
    assert restriction.dump() == {
        "nbf": 1_234_567_890,
        "exp": 1_234_567_900,
    }


def test__LegacyDateRestriction__from_parameters__empty():
    assert restrictions.LegacyDateRestriction.from_parameters() is None


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
        assert restrictions.LegacyDateRestriction.from_parameters(**kwargs) is None


@pytest.mark.parametrize(
    "kwargs, expected",
    [
        (
            {"not_before": 1_234_567_890, "not_after": 1_234_567_900},
            restrictions.LegacyDateRestriction._load_value(
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
            restrictions.LegacyDateRestriction._load_value(
                value={"nbf": 946_684_800, "exp": 4_102_444_800}
            ),
        ),
    ],
)
def test__LegacyDateRestriction__from_parameters__ok(kwargs, expected):
    assert restrictions.LegacyDateRestriction.from_parameters(**kwargs) == expected


def test__Restriction__get_subclasses():
    # This test ensures we didn't forget to add new restriction classes to
    # the set.
    assert set(restrictions.Restriction._get_subclasses()) == {
        cls
        for cls in restrictions.Restriction.__subclasses__()
        if cls.__module__ == "pypitoken.restrictions"
    }


def test__Restriction__json_load_caveat__pass():
    assert restrictions.Restriction._json_load_caveat('{"a": "b"}') == {"a": "b"}


def test__Restriction__json_load_caveat__fail():
    with pytest.raises(exceptions.LoaderError) as exc_info:
        restrictions.Restriction._json_load_caveat(caveat='{"a": "b"')
    assert (
        str(exc_info.value) == "Error while loading caveat: "
        "Expecting ',' delimiter: line 1 column 10 (char 9)"
    )


@pytest.mark.parametrize(
    "caveat, output",
    [
        (
            {"version": 1, "permissions": "user"},
            restrictions.LegacyNoopRestriction(),
        ),
        (
            {"version": 1, "permissions": {"projects": ["a", "b"]}},
            restrictions.LegacyProjectsRestriction(projects=["a", "b"]),
        ),
    ],
)
def test__Restriction__load__pass(caveat, output):
    assert restrictions.Restriction.load(caveat=caveat) == output


def test__Restriction__load__fail():
    with pytest.raises(exceptions.LoaderError) as exc_info:
        restrictions.Restriction.load(caveat={"version": 1, "permissions": "something"})
    assert (
        str(exc_info.value)
        == "Could not find matching Restriction for {'version': 1, 'permissions': 'something'}"
    )


def test__Restriction__load_json():
    restriction = restrictions.Restriction.load_json(
        caveat='{"version": 1, "permissions": "user"}'
    )
    assert restriction == restrictions.LegacyNoopRestriction()


def test__Restriction__restrictions_from_parameters():
    restriction_objs = list(
        restrictions.Restriction.restrictions_from_parameters(
            projects=["a", "b"], not_before=1, not_after=5
        )
    )
    assert restriction_objs == [
        restrictions.LegacyProjectsRestriction(projects=["a", "b"]),
        restrictions.LegacyDateRestriction(not_before=1, not_after=5),
    ]
