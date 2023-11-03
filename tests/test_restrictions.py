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
    assert noop.check(context=restrictions.Context()) is None


def test__LegacyNoopRestriction__dump():
    noop = restrictions.LegacyNoopRestriction()
    assert noop.dump() == {"version": 1, "permissions": "user"}


def test__LegacyNoopRestriction__from_parameters():
    assert (
        restrictions.LegacyNoopRestriction.from_parameters(legacy_noop=True)
        == restrictions.LegacyNoopRestriction()
    )


def test__LegacyNoopRestriction__from_parameters__other_params():
    assert restrictions.LegacyNoopRestriction.from_parameters(a=1) is None


@pytest.mark.parametrize(
    "value, restriction",
    [
        (
            {"version": 1, "permissions": {"projects": []}},
            restrictions.LegacyProjectNamesRestriction(project_names=[]),
        ),
        (
            {"version": 1, "permissions": {"projects": ["a"]}},
            restrictions.LegacyProjectNamesRestriction(project_names=["a"]),
        ),
        (
            {"version": 1, "permissions": {"projects": ["a", "b"]}},
            restrictions.LegacyProjectNamesRestriction(project_names=["a", "b"]),
        ),
    ],
)
def test__LegacyProjectNamesRestriction__load_value__pass(value, restriction):
    assert (
        restrictions.LegacyProjectNamesRestriction._load_value(value=value)
        == restriction
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
def test__LegacyProjectNamesRestriction__load_value__fail(value):
    with pytest.raises(exceptions.LoaderError):
        restrictions.LegacyProjectNamesRestriction._load_value(value=value)


def test__LegacyProjectNamesRestriction__extract_kwargs():
    value = {"version": 1, "permissions": {"projects": ["a", "b"]}}
    kwargs = restrictions.LegacyProjectNamesRestriction._extract_kwargs(value=value)
    assert kwargs == {"project_names": ["a", "b"]}


def test__LegacyProjectNamesRestriction__check__pass():
    restriction = restrictions.LegacyProjectNamesRestriction(project_names=["a", "b"])
    assert restriction.check(context=restrictions.Context(project_name="a")) is None


def test__LegacyProjectNamesRestriction__check__fail():
    restriction = restrictions.LegacyProjectNamesRestriction(project_names=["a", "b"])
    with pytest.raises(exceptions.ValidationError):
        restriction.check(context=restrictions.Context(project_name="c"))


def test__LegacyProjectNamesRestriction__check__missing_context():
    restriction = restrictions.LegacyProjectNamesRestriction(project_names=["a", "b"])
    with pytest.raises(exceptions.MissingContextError):
        restriction.check(context=restrictions.Context())


def test__LegacyProjectNamesRestriction__dump():
    restriction = restrictions.LegacyProjectNamesRestriction(project_names=["a", "b"])
    assert restriction.dump() == {
        "version": 1,
        "permissions": {"projects": ["a", "b"]},
    }


def test__LegacyProjectNamesRestriction__from_parameters__empty():
    assert restrictions.LegacyProjectNamesRestriction.from_parameters() is None


def test__LegacyProjectNamesRestriction__from_parameters__not_empty():
    assert restrictions.LegacyProjectNamesRestriction.from_parameters(
        legacy_project_names=["a", "b"]
    ) == restrictions.LegacyProjectNamesRestriction(project_names=["a", "b"])


def test__LegacyProjectNamesRestriction__from_parameters__bare_string():
    with pytest.raises(exceptions.InvalidRestriction):
        restrictions.LegacyProjectNamesRestriction.from_parameters(
            legacy_project_names="a"
        )


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
    assert restriction.check(context=restrictions.Context(now=1_234_567_895)) is None


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
        restriction.check(context=restrictions.Context(now=value))


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
        {"legacy_not_before": 1_234_567_890},
        {"legacy_not_after": 1_234_567_900},
        {
            "legacy_not_before": datetime.datetime(2000, 1, 1),
            "legacy_not_after": datetime.datetime(2100, 1, 1),
        },
    ],
)
def test__LegacyDateRestriction__from_parameters__fail(kwargs):
    with pytest.raises(exceptions.InvalidRestriction):
        restrictions.LegacyDateRestriction.from_parameters(**kwargs)


@pytest.mark.parametrize(
    "kwargs, expected",
    [
        (
            {"legacy_not_before": 1_234_567_890, "legacy_not_after": 1_234_567_900},
            restrictions.LegacyDateRestriction._load_value(
                value={"nbf": 1_234_567_890, "exp": 1_234_567_900}
            ),
        ),
        (
            {
                "legacy_not_before": datetime.datetime(
                    2000, 1, 1, tzinfo=datetime.timezone.utc
                ),
                "legacy_not_after": datetime.datetime(
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
            restrictions.LegacyProjectNamesRestriction(project_names=["a", "b"]),
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
            legacy_project_names=["a", "b"], legacy_not_before=1, legacy_not_after=5
        )
    )
    assert restriction_objs == [
        restrictions.LegacyProjectNamesRestriction(project_names=["a", "b"]),
        restrictions.LegacyDateRestriction(not_before=1, not_after=5),
    ]


def test__DateRestriction__load_value__pass():
    assert restrictions.DateRestriction._load_value(
        value=[0, 1_234_567_900, 1_234_567_890]
    ) == restrictions.DateRestriction(not_before=1_234_567_890, not_after=1_234_567_900)


@pytest.mark.parametrize(
    "value",
    [
        [],
        [1, 1_234_567_900, 1_234_567_890],
        [0],
        [0, 1_234_567_890],
        [0, 1_234_567_890, 1_234_567_999, 1_234_567_900],
        [0, "1_234_567_900", "1_234_567_890"],
        [0, "2000-01-02 00:00:00", "2000-01-01 00:00:00"],
    ],
)
def test__DateRestriction__load_value__fail(value):
    with pytest.raises(exceptions.LoaderError):
        restrictions.DateRestriction._load_value(value=value)


def test__DateRestriction__extract_kwargs():
    value = [0, 1_234_567_900, 1_234_567_890]
    kwargs = restrictions.DateRestriction._extract_kwargs(value=value)
    assert kwargs == {"not_before": 1_234_567_890, "not_after": 1_234_567_900}


def test__DateRestriction__check__pass():
    restriction = restrictions.DateRestriction(
        not_before=1_234_567_890, not_after=1_234_567_900
    )
    assert restriction.check(context=restrictions.Context(now=1_234_567_895)) is None


@pytest.mark.parametrize(
    "value",
    [
        1_234_567_000,
        1_234_568_000,
    ],
)
def test__DateRestriction__check__fail(value):
    restriction = restrictions.DateRestriction(
        not_before=1_234_567_890, not_after=1_234_567_900
    )
    with pytest.raises(exceptions.ValidationError):
        restriction.check(context=restrictions.Context(now=value))


def test__DateRestriction__dump():
    restriction = restrictions.DateRestriction(
        not_before=1_234_567_890, not_after=1_234_567_900
    )
    assert restriction.dump() == [0, 1_234_567_900, 1_234_567_890]


def test__DateRestriction__from_parameters__empty():
    assert restrictions.DateRestriction.from_parameters() is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"not_before": 1_234_567_890},
        {"not_after": 1_234_567_900},
        {  # tz-naive
            "not_before": datetime.datetime(2000, 1, 1),
            "not_after": datetime.datetime(2100, 1, 1),
        },
    ],
)
def test__DateRestriction__from_parameters__fail(kwargs):
    with pytest.raises(exceptions.InvalidRestriction):
        restrictions.DateRestriction.from_parameters(**kwargs)


@pytest.mark.parametrize(
    "kwargs, expected",
    [
        (
            {"not_before": 1_234_567_890, "not_after": 1_234_567_900},
            restrictions.DateRestriction(
                not_before=1_234_567_890, not_after=1_234_567_900
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
            restrictions.DateRestriction(
                not_before=946_684_800, not_after=4_102_444_800
            ),
        ),
    ],
)
def test__DateRestriction__from_parameters__ok(kwargs, expected):
    assert restrictions.DateRestriction.from_parameters(**kwargs) == expected


@pytest.mark.parametrize(
    "value, restriction",
    [
        (
            [1, []],
            restrictions.ProjectNamesRestriction(project_names=[]),
        ),
        (
            [1, ["a"]],
            restrictions.ProjectNamesRestriction(project_names=["a"]),
        ),
        (
            [1, ["a", "b"]],
            restrictions.ProjectNamesRestriction(project_names=["a", "b"]),
        ),
        (
            [1, ["a", "aa", "a-a", "aaa--aaa"]],
            restrictions.ProjectNamesRestriction(
                project_names=["a", "aa", "a-a", "aaa--aaa"]
            ),
        ),
    ],
)
def test__ProjectNamesRestriction__load_value__pass(value, restriction):
    assert restrictions.ProjectNamesRestriction._load_value(value=value) == restriction


@pytest.mark.parametrize(
    "value",
    [
        [],
        [0, ["a"]],
        [1, ["a"], ["a"]],
        [1, "a"],
        [1, [1]],
        [1, ["a", 1]],
    ],
)
def test__ProjectNamesRestriction__load_value__fail(value):
    with pytest.raises(exceptions.LoaderError):
        restrictions.ProjectNamesRestriction._load_value(value=value)


def test__ProjectNamesRestriction__extract_kwargs():
    value = [1, ["a", "b"]]
    kwargs = restrictions.ProjectNamesRestriction._extract_kwargs(value=value)
    assert kwargs == {"project_names": ["a", "b"]}


def test__ProjectNamesRestriction__check__pass():
    restriction = restrictions.ProjectNamesRestriction(project_names=["a", "b"])
    assert restriction.check(context=restrictions.Context(project_name="a")) is None


def test__ProjectNamesRestriction__check__fail():
    restriction = restrictions.ProjectNamesRestriction(project_names=["a", "b"])
    with pytest.raises(exceptions.ValidationError):
        restriction.check(context=restrictions.Context(project_name="c"))


def test__ProjectNamesRestriction__check__missing_context():
    restriction = restrictions.ProjectNamesRestriction(project_names=["a", "b"])
    with pytest.raises(exceptions.MissingContextError):
        restriction.check(context=restrictions.Context())


def test__ProjectNamesRestriction__dump():
    restriction = restrictions.ProjectNamesRestriction(project_names=["a", "b"])
    assert restriction.dump() == [1, ["a", "b"]]


def test__ProjectNamesRestriction__from_parameters__empty():
    assert restrictions.ProjectNamesRestriction.from_parameters() is None


def test__ProjectNamesRestriction__from_parameters__bare_string():
    with pytest.raises(exceptions.InvalidRestriction):
        restrictions.ProjectNamesRestriction.from_parameters(project_names="a")


def test__ProjectNamesRestriction__from_parameters__not_empty():
    assert restrictions.ProjectNamesRestriction.from_parameters(
        project_names=["a", "b"]
    ) == restrictions.ProjectNamesRestriction(project_names=["a", "b"])


@pytest.mark.parametrize(
    "value, restriction",
    [
        (
            [2, []],
            restrictions.ProjectIDsRestriction(project_ids=[]),
        ),
        (
            [2, ["00000000-0000-0000-0000-000000000000"]],
            restrictions.ProjectIDsRestriction(
                project_ids=["00000000-0000-0000-0000-000000000000"]
            ),
        ),
        (
            [
                2,
                [
                    "00000000-0000-0000-0000-000000000000",
                    "00000000-0000-0000-0000-000000000001",
                ],
            ],
            restrictions.ProjectIDsRestriction(
                project_ids=[
                    "00000000-0000-0000-0000-000000000000",
                    "00000000-0000-0000-0000-000000000001",
                ]
            ),
        ),
    ],
)
def test__ProjectIDsRestriction__load_value__pass(value, restriction):
    assert restrictions.ProjectIDsRestriction._load_value(value=value) == restriction


@pytest.mark.parametrize(
    "value",
    [
        [],
        [0, ["00000000-0000-0000-0000-000000000000"]],
        [
            2,
            ["00000000-0000-0000-0000-000000000000"],
            ["00000000-0000-0000-0000-000000000001"],
        ],
        [2, "00000000-0000-0000-0000-000000000000"],
        [2, [1]],
        [2, ["00000000-0000-0000-0000-000000000000", 1]],
    ],
)
def test__ProjectIDsRestriction__load_value__fail(value):
    with pytest.raises(exceptions.LoaderError):
        restrictions.ProjectIDsRestriction._load_value(value=value)


def test__ProjectIDsRestriction__extract_kwargs():
    value = [2, ["00000000-0000-0000-0000-000000000000"]]
    kwargs = restrictions.ProjectIDsRestriction._extract_kwargs(value=value)
    assert kwargs == {"project_ids": ["00000000-0000-0000-0000-000000000000"]}


def test__ProjectIDsRestriction__check__pass():
    restriction = restrictions.ProjectIDsRestriction(
        project_ids=["00000000-0000-0000-0000-000000000000"]
    )
    assert (
        restriction.check(
            context=restrictions.Context(
                project_id="00000000-0000-0000-0000-000000000000"
            )
        )
        is None
    )


def test__ProjectIDsRestriction__check__fail():
    restriction = restrictions.ProjectIDsRestriction(
        project_ids=[
            "00000000-0000-0000-0000-000000000000",
            "00000000-0000-0000-0000-000000000001",
        ]
    )
    with pytest.raises(exceptions.ValidationError):
        restriction.check(
            context=restrictions.Context(
                project_id="00000000-0000-0000-0000-000000000002"
            )
        )


def test__ProjectIDsRestriction__check__missing_context():
    restriction = restrictions.ProjectIDsRestriction(
        project_ids=["00000000-0000-0000-0000-000000000000"]
    )
    with pytest.raises(exceptions.MissingContextError):
        restriction.check(context=restrictions.Context())


def test__ProjectIDsRestriction__dump():
    restriction = restrictions.ProjectIDsRestriction(
        project_ids=[
            "00000000-0000-0000-0000-000000000000",
            "00000000-0000-0000-0000-000000000001",
        ]
    )
    assert restriction.dump() == [
        2,
        [
            "00000000-0000-0000-0000-000000000000",
            "00000000-0000-0000-0000-000000000001",
        ],
    ]


def test__ProjectIDsRestriction__from_parameters__empty():
    assert restrictions.ProjectIDsRestriction.from_parameters() is None


def test__ProjectIDsRestriction__from_parameters__bare_string():
    with pytest.raises(exceptions.InvalidRestriction):
        restrictions.ProjectIDsRestriction.from_parameters(
            project_ids="00000000-0000-0000-0000-000000000000"
        )


def test__ProjectIDsRestriction__from_parameters__not_empty():
    assert restrictions.ProjectIDsRestriction.from_parameters(
        project_ids=[
            "00000000-0000-0000-0000-000000000000",
            "00000000-0000-0000-0000-000000000001",
        ]
    ) == restrictions.ProjectIDsRestriction(
        project_ids=[
            "00000000-0000-0000-0000-000000000000",
            "00000000-0000-0000-0000-000000000001",
        ]
    )


@pytest.mark.parametrize(
    "value, restriction",
    [
        (
            [3, "00000000-0000-0000-0000-000000000000"],
            restrictions.UserIDRestriction(
                user_id="00000000-0000-0000-0000-000000000000"
            ),
        ),
    ],
)
def test__UserIDRestriction__load_value__pass(value, restriction):
    assert restrictions.UserIDRestriction._load_value(value=value) == restriction


@pytest.mark.parametrize(
    "value",
    [
        [],
        [0, "00000000-0000-0000-0000-000000000000"],
        [3],
        [
            3,
            "00000000-0000-0000-0000-000000000000",
            "00000000-0000-0000-0000-000000000001",
        ],
        [3, "aaaaa"],
        [3, "01"],
    ],
)
def test__UserIDRestriction__load_value__fail(value):
    with pytest.raises(exceptions.LoaderError):
        restrictions.UserIDRestriction._load_value(value=value)


def test__UserIDRestriction__extract_kwargs():
    value = [3, "00000000-0000-0000-0000-000000000000"]
    kwargs = restrictions.UserIDRestriction._extract_kwargs(value=value)
    assert kwargs == {"user_id": "00000000-0000-0000-0000-000000000000"}


def test__UserIDRestriction__check__pass():
    restriction = restrictions.UserIDRestriction(
        user_id="00000000-0000-0000-0000-000000000000"
    )
    assert (
        restriction.check(
            context=restrictions.Context(user_id="00000000-0000-0000-0000-000000000000")
        )
        is None
    )


def test__UserIDRestriction__check__fail():
    restriction = restrictions.UserIDRestriction(
        user_id="00000000-0000-0000-0000-000000000000"
    )
    with pytest.raises(exceptions.ValidationError):
        restriction.check(
            context=restrictions.Context(user_id="00000000-0000-0000-0000-000000000002")
        )


def test__UserIDRestriction__check__missing_context():
    restriction = restrictions.UserIDRestriction(
        user_id="00000000-0000-0000-0000-000000000000"
    )
    with pytest.raises(exceptions.MissingContextError):
        restriction.check(context=restrictions.Context())


def test__UserIDRestriction__dump():
    restriction = restrictions.UserIDRestriction(
        user_id="00000000-0000-0000-0000-000000000000"
    )
    assert restriction.dump() == [3, "00000000-0000-0000-0000-000000000000"]


def test__UserIDRestriction__from_parameters__empty():
    assert restrictions.UserIDRestriction.from_parameters() is None


def test__UserIDRestriction__from_parameters__not_empty():
    assert restrictions.UserIDRestriction.from_parameters(
        user_id="00000000-0000-0000-0000-000000000000"
    ) == restrictions.UserIDRestriction(user_id="00000000-0000-0000-0000-000000000000")
