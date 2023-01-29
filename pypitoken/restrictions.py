from __future__ import annotations

import dataclasses
import datetime
import json
import time
from typing import Any, ClassVar, Iterable, TypeVar

import jsonschema

from pypitoken import exceptions


@dataclasses.dataclass(init=False)
class Context:
    """
    Describe the circumstances sourrounding how the bearer is attempting to use
    the token. Will be checked against restriction to determine whether the bearer
    can or cannot use this token for the operation.

    Parameters
    ----------
    project_name :
        Normalized name of the project the bearer is attempting to upload to
    project_id :
        ID of the project the bearer is attempting to upload to
    user_id :
        ID of the user that is attempting to upload
    now :
        timestamp of the current time, to check date/time-related restrictions.
        Defaults to now.
    """

    # It's expected that no attribute has a default value. Defaults are encoded
    # in __init__ (that's all because the initial values don't match the attribute
    # types)
    project_name: str | None
    project_id: str | None
    user_id: str | None
    now: int

    def __init__(
        self,
        project_name: str | None = None,
        project_id: str | None = None,
        user_id: str | None = None,
        now: int | datetime.datetime | None = None,
    ):
        self.project_name = project_name
        self.project_id = project_id
        self.user_id = user_id

        if now is None:
            self.now = int(time.time())
        else:
            self.now = timestamp_from_parameter(now)


TR = TypeVar("TR", bound="Restriction")


# Making the class a dataclass is mainly meant to ease comparison using ==
@dataclasses.dataclass
class Restriction:
    """
    Base Restriction class.

    Expose lower-level methods for restriction/caveat introspection.
    """

    needs_context: ClassVar[list[str]] = []

    @staticmethod
    def _get_schema() -> dict:
        """
        Return a jsonschema Dict object used to validate the format
        of a json restriction.
        """
        raise NotImplementedError

    @classmethod
    def _load_value(cls: type[TR], value: dict) -> TR:
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
        schema = cls._get_schema()
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
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
        return [
            DateRestriction,
            ProjectNamesRestriction,
            ProjectIDsRestriction,
            UserIDRestriction,
            # Legacy
            LegacyNoopRestriction,
            LegacyProjectNamesRestriction,
            LegacyDateRestriction,
        ]

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
    def _extract_kwargs(cls, value: Any) -> dict:
        """
        Receive the parsed JSON value of a caveat for which the schema has been
        validated. Return the instantiation kwargs (``__init__`` parameters).
        """
        raise NotImplementedError

    @classmethod
    def from_parameters(cls: type[TR], **kwargs) -> TR | None:
        """
        Constructs an instance from the parameters passed to `Token.restrict`
        """
        raise NotImplementedError

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
        `MissingContextError`
            (a subclass of ValidationError): Restriction is unmet because the
            context is lacking required values. This is more probably a code issue
            from the `Token.check` call than an issue with the token itself,
            though it also means that the token should be rejected.
        """
        for need in self.needs_context:
            if getattr(context, need) is None:
                raise exceptions.MissingContextError(
                    "The restriction couldn't be checked because the context is missing required values"
                )

    def dump(self) -> dict | list:
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
class DateRestriction(Restriction):
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
    # https://github.com/pypi/warehouse/blob/606bce63472a7979eff0a37ea8c44c335b9c118f/warehouse/macaroons/caveats/__init__.py#L41
    tag: ClassVar[int] = 0
    needs_context: ClassVar[list[str]] = ["now"]

    @classmethod
    def _get_schema(cls) -> dict:
        return {
            "type": "array",
            "prefixItems": [
                {"type": "integer", "const": cls.tag},
                {"type": "integer"},
                {"type": "integer"},
            ],
            "items": False,
            "minItems": 3,
            "maxItems": 3,
        }

    @classmethod
    def _extract_kwargs(cls, value: list) -> dict:
        return {
            "not_before": value[2],  # Yes, the official order is "reversed"
            "not_after": value[1],
        }

    def dump(self) -> list:
        return [self.tag, self.not_after, self.not_before]

    def check(self, context: Context) -> None:
        super().check(context=context)
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
        not_before: int | datetime.datetime | None = None,
        not_after: int | datetime.datetime | None = None,
        **kwargs,
    ) -> DateRestriction | None:
        if not (not_before or not_after):
            return None

        if not (not_before and not_after):
            raise exceptions.InvalidRestriction(
                "`not_before` and `not_after` parameters must be used together. "
                "Either define both or neither. "
                f"Received not_before={not_before} and not_after={not_after}"
            )
        return cls(
            not_before=timestamp_from_parameter(not_before),
            not_after=timestamp_from_parameter(not_after),
        )


@dataclasses.dataclass
class ProjectNamesRestriction(Restriction):
    """
    Restrict a `Token` to uploading releases for project with specific names.

    Attributes
    ----------
    project_names :
        Normalized project names this token may upload to.
    """

    project_names: list[str]
    # https://github.com/pypi/warehouse/blob/606bce63472a7979eff0a37ea8c44c335b9c118f/warehouse/macaroons/caveats/__init__.py#L54
    tag: ClassVar[int] = 1
    needs_context: ClassVar[list[str]] = ["project_name"]

    @classmethod
    def _get_schema(cls) -> dict:
        return {
            "type": "array",
            "prefixItems": [
                {"type": "integer", "const": cls.tag},
                {
                    "type": "array",
                    "items": {
                        "type": "string",
                        # Regex from https://peps.python.org/pep-0426/#name
                        # with normalization rule from
                        # https://peps.python.org/pep-0503/#normalized-names
                        "pattern": r"^([a-z0-9]|[a-z0-9][a-z0-9-]*[a-z0-9])$",
                    },
                },
            ],
            "minItems": 2,
            "maxItems": 2,
            "items": False,
        }

    @classmethod
    def _extract_kwargs(cls, value: list) -> dict:
        return {"project_names": value[1]}

    def dump(self) -> list:
        return [self.tag, self.project_names]

    def check(self, context: Context) -> None:
        super().check(context=context)
        project_name = context.project_name

        if project_name not in self.project_names:
            raise exceptions.ValidationError(
                f"This token can only be used for project(s): "
                f"{', '.join(self.project_names)}. Received: {project_name}"
            )

    @classmethod
    def from_parameters(
        cls,
        project_names: list[str] | None = None,
        **kwargs,
    ) -> ProjectNamesRestriction | None:
        if project_names is not None:
            return cls(project_names=project_names)
        return None


@dataclasses.dataclass
class ProjectIDsRestriction(Restriction):
    """
    Restrict a `Token` to uploading releases for project with specific IDs.

    Attributes
    ----------
    project_ids :
        Project IDs this token may upload to.
    """

    project_ids: list[str]
    # https://github.com/pypi/warehouse/blob/606bce63472a7979eff0a37ea8c44c335b9c118f/warehouse/macaroons/caveats/__init__.py#L71
    tag: ClassVar[int] = 2
    needs_context: ClassVar[list[str]] = ["project_id"]

    @classmethod
    def _get_schema(cls) -> dict:
        return {
            "type": "array",
            "prefixItems": [
                {"type": "integer", "const": cls.tag},
                {
                    "type": "array",
                    "items": {
                        "type": "string",
                        # Uppercase UUIDs are not accepted
                        "pattern": r"^[0-9a-f]{8}\b-[0-9a-f]{4}\b-[0-9a-f]{4}\b-[0-9a-f]{4}\b-[0-9a-f]{12}$",
                    },
                },
            ],
            "minItems": 2,
            "maxItems": 2,
            "items": False,
        }

    @classmethod
    def _extract_kwargs(cls, value: list) -> dict:
        return {"project_ids": value[1]}

    def dump(self) -> list:
        return [self.tag, self.project_ids]

    def check(self, context: Context) -> None:
        super().check(context=context)
        project_id = context.project_id

        if project_id not in self.project_ids:
            raise exceptions.ValidationError(
                f"This token can only be used for project(s): "
                f"{', '.join(self.project_ids)}. Received: {project_id}"
            )

    @classmethod
    def from_parameters(
        cls,
        project_ids: list[str] | None = None,
        **kwargs,
    ) -> ProjectIDsRestriction | None:
        if project_ids is not None:
            return cls(project_ids=project_ids)
        return None


@dataclasses.dataclass
class UserIDRestriction(Restriction):
    """
    Restrict a `Token` to being used by the user with the corresponding ID.

    Attributes
    ----------
    user_id :
        ID of the user that may use this token.
    """

    user_id: str
    # https://github.com/pypi/warehouse/blob/606bce63472a7979eff0a37ea8c44c335b9c118f/warehouse/macaroons/caveats/__init__.py#L88
    tag: ClassVar[int] = 3
    needs_context: ClassVar[list[str]] = ["user_id"]

    @classmethod
    def _get_schema(cls) -> dict:
        return {
            "type": "array",
            "prefixItems": [
                {"type": "integer", "const": cls.tag},
                {
                    "type": "string",
                    # Uppercase ID is not accepted
                    "pattern": r"^[0-9a-f]{8}\b-[0-9a-f]{4}\b-[0-9a-f]{4}\b-[0-9a-f]{4}\b-[0-9a-f]{12}$",
                },
            ],
            "minItems": 2,
            "maxItems": 2,
            "items": False,
        }

    @classmethod
    def _extract_kwargs(cls, value: list) -> dict:
        return {"user_id": value[1]}

    def dump(self) -> list:
        return [self.tag, self.user_id]

    def check(self, context: Context) -> None:
        super().check(context=context)
        user_id = context.user_id

        if user_id != self.user_id:
            raise exceptions.ValidationError(
                f"This token can only be used by user with id: "
                f"{self.user_id}. Received: {user_id}"
            )

    @classmethod
    def from_parameters(
        cls,
        user_id: str | None = None,
        **kwargs,
    ) -> UserIDRestriction | None:
        if user_id is not None:
            return cls(user_id=user_id)
        return None


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
        super().check(context=context)
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
class LegacyProjectNamesRestriction(Restriction):
    """
    Restrict a `Token` to uploading releases for a specific set of packages.

    Attributes
    ----------
    projects :
        Normalized project names this token may upload to.
    """

    project_names: list[str]
    needs_context: ClassVar[list[str]] = ["project_name"]

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
        super().check(context=context)
        project_name = context.project_name

        if project_name not in self.project_names:
            raise exceptions.ValidationError(
                f"This token can only be used for project(s): "
                f"{', '.join(self.project_names)}. Received: {project_name}"
            )

    @classmethod
    def from_parameters(
        cls,
        legacy_project_names: list[str] | None = None,
        **kwargs,
    ) -> LegacyProjectNamesRestriction | None:
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
    needs_context: ClassVar[list[str]] = ["now"]

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
        super().check(context=context)
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
        legacy_not_before: int | datetime.datetime | None = None,
        legacy_not_after: int | datetime.datetime | None = None,
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


def timestamp_from_parameter(param: int | datetime.datetime) -> int:
    if isinstance(param, int):
        return int(param)
    # https://docs.python.org/3/library/datetime.html#determining-if-an-object-is-aware-or-naive
    naive = param.tzinfo is None or param.tzinfo.utcoffset(param) is None
    if naive:
        raise exceptions.InvalidRestriction(
            "Cannot use a naive datetime. Either provide a timezone or "
            "the timestamp directly. "
            "Received {param}"
        )
    return int(param.timestamp())
