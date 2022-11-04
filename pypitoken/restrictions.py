from __future__ import annotations

import dataclasses
import datetime
import json
import time
from typing import Any, Iterable, TypeVar

import jsonschema

from pypitoken import exceptions, utils


@dataclasses.dataclass
class Context:
    """
    Describe the circumstances sourrounding how the bearer is attempting to use
    the token. Will be checked against restriction to determine whether the bearer
    can or cannot use this token for the operation.

    Parameters
    ----------
    project :
        Normalized name of the project the bearer is attempting to upload to
    """

    project_name: str
    project_id: str
    user_id: str
    now: int = dataclasses.field(default_factory=lambda: int(time.time()))


T = TypeVar("T", bound="Restriction")


# Making the class a dataclass is mainly meant to ease comparison using ==
@dataclasses.dataclass
class Restriction:
    """
    Base Restriction class.

    Expose lower-level methods for restriction/caveat introspection.
    """

    @staticmethod
    def _get_schema() -> dict:
        """
        Return a jsonschema Dict object used to validate the format
        of a json restriction.
        """
        raise NotImplementedError

    @classmethod
    def _load_value(cls: type[T], value: dict) -> T:
        """
        Create a Restriction from the JSON value stored in the caveat

        Raises
        ------
        exceptions.LoaderError
            Raise when the JSON format doesn't match this class' restriction format

        Returns
        -------
        Restriction
        """
        try:
            jsonschema.validate(
                instance=value,
                schema=cls._get_schema(),
            )
        except jsonschema.ValidationError as exc:
            raise exceptions.LoaderError() from exc

        return cls(**cls._extract_kwargs(value=value))  # type: ignore

    @staticmethod
    def _get_subclasses() -> list[type[Restriction]]:
        """
        List all subclasses of Restriction that we want to match against
        """
        # We could use __subclasses__ but that could lead to all kinds of funky things,
        # especially in a security-sensistive library.
        # Tests will check this against Restriction subclasses though.
        return [LegacyNoopRestriction, LegacyProjectsRestriction, LegacyDateRestriction]

    @staticmethod
    def _json_load_caveat(caveat: str) -> Any:
        try:
            value = json.loads(caveat)
        except Exception as exc:
            raise exceptions.LoaderError(f"Error while loading caveat: {exc}") from exc

        return value

    @classmethod
    def load(cls, caveat: dict) -> Restriction:
        """
        Create a Restriction from a raw caveat restriction JSON object.

        Raises
        ------
        pypitokens.LoaderError
            If the format cannot be understood

        Returns
        -------
        `Restriction`
        """
        for subclass in cls._get_subclasses():
            try:
                return subclass._load_value(value=caveat)
            except exceptions.LoaderError:
                continue

        raise exceptions.LoaderError(
            f"Could not find matching Restriction for {caveat}"
        )

    @classmethod
    def load_json(cls, caveat: str) -> Restriction:
        """
        Create a Restriction from a raw caveat restriction JSON string.

        Raises
        ------
        pypitokens.LoaderError
            If the format cannot be understood

        Returns
        -------
        `Restriction`
        """
        caveat_obj = cls._json_load_caveat(caveat=caveat)
        return cls.load(caveat=caveat_obj)

    @classmethod
    def _extract_kwargs(cls, value: dict) -> dict:
        """
        Receive the parsed JSON value of a caveat for which the schema has been
        validated. Return the instantiation kwargs (``__init__`` parameters).
        """
        raise NotImplementedError

    @classmethod
    def from_parameters(cls: type[T], **kwargs) -> T | None:
        """
        Constructs an instance from the parameters passed to `Token.restrict`
        """
        raise NotImplementedError

    @classmethod
    def restriction_parameters(cls):
        return utils.merge_parameters(
            *(subclass.from_parameters for subclass in cls._get_subclasses())
        )

    @classmethod
    def restrictions_from_parameters(cls, **kwargs) -> Iterable[Restriction]:
        """
        Constructs an iterable of Restriction subclass instances from the parameters
        passed to `Token.restrict`
        """
        for subclass in cls._get_subclasses():
            restriction = subclass.from_parameters(**kwargs)
            if restriction:
                yield restriction

    def check(self, context: Context) -> None:
        """
        Receive the context of a check

        Parameters
        ----------
        context :
            Describes how the bearer is attempting to use the token.

        Raises
        ------
        `ValidationError`
            Restriction was checked and appeared unmet.
        """
        raise NotImplementedError

    def dump(self) -> dict:
        """
        Transform a restriction into a JSON-compatible dict object
        """
        raise NotImplementedError

    def dump_json(self) -> str:
        """
        Transform a restriction into a JSON-encoded string
        """
        return json.dumps(self.dump())


@dataclasses.dataclass
class LegacyNoopRestriction(Restriction):
    """
    Says it restricts the `Token`, but doesn't actually restrict it.
    """

    @staticmethod
    def _get_schema() -> dict:
        return {
            "type": "object",
            "properties": {
                "version": {"type": "integer", "const": 1},
                "permissions": {"type": "string", "const": "user"},
            },
            "required": ["version", "permissions"],
            "additionalProperties": False,
        }

    @classmethod
    def _extract_kwargs(cls, value: dict) -> dict:
        return {}

    def check(self, context: Context) -> None:
        # Always passes
        return

    def dump(self) -> dict:
        return {"version": 1, "permissions": "user"}

    @classmethod
    def from_parameters(
        cls,
        legacy_noop: bool | None = None,
        **kwargs,
    ) -> LegacyNoopRestriction | None:
        if legacy_noop is True:
            return cls()
        return None


@dataclasses.dataclass
class LegacyProjectsRestriction(Restriction):
    """
    Restrict a `Token` to uploading releases for a specific set of packages.

    Attributes
    ----------
    projects :
        Normalized project names this token may upload to.
    """

    project_names: list[str]

    @staticmethod
    def _get_schema() -> dict:
        return {
            "type": "object",
            "properties": {
                "version": {"type": "integer", "const": 1},
                "permissions": {
                    "type": "object",
                    "properties": {
                        "projects": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["projects"],
                    "additionalProperties": False,
                },
            },
            "required": ["version", "permissions"],
            "additionalProperties": False,
        }

    @classmethod
    def _extract_kwargs(cls, value: dict) -> dict:
        return {"project_names": value["permissions"]["projects"]}

    def dump(self) -> dict:
        return {"version": 1, "permissions": {"projects": self.project_names}}

    def check(self, context: Context) -> None:
        project = context.project_name

        if project not in self.project_names:
            raise exceptions.ValidationError(
                f"This token can only be used for project(s): "
                f"{', '.join(self.project_names)}. Received: {project}"
            )

    @classmethod
    def from_parameters(
        cls,
        legacy_project_names: list[str] | None = None,
        **kwargs,
    ) -> LegacyProjectsRestriction | None:
        if legacy_project_names is not None:
            return cls(project_names=legacy_project_names)
        return None


@dataclasses.dataclass
class LegacyDateRestriction(Restriction):
    """
    Restrict a `Token` to a single time interval.

    Attributes
    ----------
    not_before :
        Token is not to be used before this Unix timestamp.
    not_after :
        Token is not to be used after this Unix timestamp.

    """

    not_before: int
    not_after: int

    @staticmethod
    def _get_schema() -> dict:
        return {
            "type": "object",
            "properties": {
                "nbf": {"type": "integer"},
                "exp": {"type": "integer"},
            },
            "required": ["nbf", "exp"],
            "additionalProperties": False,
        }

    @classmethod
    def _extract_kwargs(cls, value: dict) -> dict:
        return {
            "not_before": value["nbf"],
            "not_after": value["exp"],
        }

    def dump(self) -> dict:
        return {"nbf": self.not_before, "exp": self.not_after}

    def check(self, context: Context) -> None:
        now: int = context.now

        if not self.not_before <= now < self.not_after:
            raise exceptions.ValidationError(
                f"This token can only be used between timestamps "
                f"{self.not_before} (incl) and {self.not_after} (excl). "
                f"Received: {now}"
            )

    @classmethod
    def from_parameters(
        cls,
        legacy_not_before: datetime.datetime | int | None = None,
        legacy_not_after: datetime.datetime | int | None = None,
        **kwargs,
    ) -> LegacyDateRestriction | None:
        if legacy_not_before or legacy_not_after:
            if not (legacy_not_before and legacy_not_after):
                raise exceptions.InvalidRestriction(
                    "`legacy_not_before` and `legacy_not_after` parameters "
                    "must be used together. Either define both or neither. "
                    f"Received legacy_not_before={legacy_not_before} and "
                    f"legacy_not_after={legacy_not_after}"
                )
            return cls(
                not_before=timestamp_from_parameter(legacy_not_before),
                not_after=timestamp_from_parameter(legacy_not_after),
            )
        return None


def timestamp_from_parameter(param: datetime.datetime | int) -> int:
    if isinstance(param, int):
        return param
    # https://docs.python.org/3/library/datetime.html#determining-if-an-object-is-aware-or-naive
    naive = param.tzinfo is None or param.tzinfo.utcoffset(param) is None
    if naive:
        raise exceptions.InvalidRestriction(
            "Cannot use a naive datetime. Either provide a timezone or "
            "the timestamp directly. "
            "Received {param}"
        )
    return int(param.timestamp())
