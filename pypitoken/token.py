from __future__ import annotations

import dataclasses
import datetime
import functools
import json
import time
from typing import Any, Iterable, TypeVar

import jsonschema
import pymacaroons

from pypitoken import exceptions, utils

PREFIX = "pypi"


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

    project: str
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
        return [NoopRestriction, ProjectsRestriction, DateRestriction]

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
        Contructs an instance from the parameters passed to `Token.restrict`
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
        Contructs an iterable of Restriction subclass instances from the parameters
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
class NoopRestriction(Restriction):
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
    def from_parameters(cls, **kwargs) -> NoopRestriction | None:
        if not kwargs:
            return cls()
        return None


@dataclasses.dataclass
class ProjectsRestriction(Restriction):
    """
    Restrict a `Token` to uploading releases for a specific set of packages.

    Attributes
    ----------
    projects :
        Normalized project names this token may upload to.
    """

    projects: list[str]

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
        return {"projects": value["permissions"]["projects"]}

    def dump(self) -> dict:
        return {"version": 1, "permissions": {"projects": self.projects}}

    def check(self, context: Context) -> None:
        project = context.project

        if project not in self.projects:
            raise exceptions.ValidationError(
                f"This token can only be used for project(s): "
                f"{', '.join(self.projects)}. Received: {project}"
            )

    @classmethod
    def from_parameters(
        cls,
        projects: list[str] | None = None,
        **kwargs,
    ) -> ProjectsRestriction | None:
        if projects is not None:
            return cls(projects=projects)
        return None


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
        not_before: datetime.datetime | int | None = None,
        not_after: datetime.datetime | int | None = None,
        **kwargs,
    ) -> DateRestriction | None:
        if not_before or not_after:
            if not (not_before and not_after):
                raise exceptions.InvalidRestriction(
                    "`not_before` and `not_after` parameters must be used together. "
                    "Either define both or neither. "
                    f"Received not_before={not_before} and not_after={not_after}"
                )
            return cls(
                not_before=cls.timestamp_from_parameter(not_before),
                not_after=cls.timestamp_from_parameter(not_after),
            )
        return None

    @staticmethod
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


class Token:
    """
    Create a `Token` (as PyPI itself would do), load an existing
    `Token`, create additional restrictions on a `Token` and dump a `Token` string
    from a `Token`.

    This class is an higher level abstraction over the Macaroons from pymacaroons,
    with specific knowledge of their implementation within PyPI.

    Attributes
    ----------
    prefix : str
        PyPI tokens are usually prefixed with ``pypi``, but this is arbitrary
    domain : str
        PyPI tokens are attached to a specific domain, usually ``pypi.org`` or
        ``test.pypi.org``
    identifier : str
        This part is how PyPI will find a token in its database and associate it to a
        specific user. Even when additional restrictions are added to a token, the
        identifier will still be readable in the token. While this is not exactly
        a secret part of the token, it's best to keep it reasonably private.
    _macaroon : pymacarrons.Macaroon
        This is part of the private API and may be subject to change at any time.
        This gives you access to the underlying Macaroon, if you need to do low-level
        operations, or just want to poke around.
    """

    def __init__(self, prefix: str, macaroon: pymacaroons.Macaroon):
        """
        This constructor is usually not meant to be called directly, use either
        `create` or `load` to get `Token` instances.

        Parameters
        ----------
        prefix :
            prefix of the token, usually `pypi`
        macaroon :
            Macaroon containing all the token data
        """
        self.prefix = prefix
        self._macaroon = macaroon

    @property
    def domain(self) -> str:
        return self._macaroon.location

    @property
    def identifier(self) -> str:
        return self._macaroon.identifier.decode("utf-8")

    @classmethod
    def load(cls, raw: str) -> Token:
        """
        Deserialize a `Token` from a raw string.
        Warning: does NOT check for the Token validity, you need to call `check`
        for that.

        Parameters
        ----------
        raw :
            The token string (including the prefix)

        Returns
        -------
        Token
            Loaded token

        Raises
        ------
        `pypitoken.LoaderError`
            Any error in loading the token will be raised as a LoaderError.
            The original exception (if any) will be attached
            as the exception cause (``raise from``).
        """
        try:
            prefix, raw_macaroon = raw.split("-", maxsplit=1)
        except ValueError:
            raise exceptions.LoaderError("Token is missing a prefix")
        try:
            macaroon = pymacaroons.Macaroon.deserialize(raw_macaroon)
        # https://github.com/ecordell/pymacaroons/issues/50
        except Exception as exc:
            raise exceptions.LoaderError(f"Deserialization error: {exc}") from exc
        return cls(
            prefix=prefix,
            macaroon=macaroon,
        )

    @classmethod
    def create(
        cls,
        domain: str,
        identifier: str,
        key: str | bytes,
        prefix: str = PREFIX,
        version: int = pymacaroons.MACAROON_V2,
    ) -> Token:
        """
        Create a token. Initially, it has no restruction, but they can be added
        with restrict.
        In order to create the token, you will need to provide a key. This key is the
        secret part of the token. When checking a macaroon validity, you will need to
        provide the same key.

        Parameters
        ----------
        domain :
            PyPI tokens are attached to a specific domain, usually ``pypi.org`` or
            ``test.pypi.org``.
        identifier :
            Identifies the Token (and its associated user) in the PyPI database.
        key :
            Secret key used to validate the token. Having the key of a token would
            allow removing existing restrictions.
        prefix :
            PyPI tokens are usually prefixed with ``pypi`` which is the default value
            for this parameter.
        version :
            Version of the pymacaroons specification to use. There's probably no reason
            we would want to change this.

        Returns
        -------
        `Token`
            The newly minted token
        """
        macaroon = pymacaroons.Macaroon(
            location=domain,
            identifier=identifier,
            key=key,
            version=version,
        )
        token = cls(prefix=prefix, macaroon=macaroon)
        return token

    def restrict(self, **kwargs) -> Token:
        """
        Modifies the token in-place to add restrictions to it. This can be called by
        PyPI as well as by anyone, adding restrictions to new or existing tokens.

        Note that if no parameter is passed, and the token has no other restrictions
        already, this method will still add a noop restriction, to match the original
        implementation.

        Note: a token allows the owner to delegate their rights to the bearer.
        Consequently, a token adding restrictions linked to a project that the owner
        cannot use will not make its bearer able to upload releases to the project. As
        stated in the name, restrictions can reduce the scope of a token, and cannot
        broaden it. It's possible to create a token that can do nothing, for example by
        adding two incompatible restrictions.

        Parameters
        ----------
        projects :
            Restrict the token to uploading releases only for projects with these
            normalized names, by default None (no restriction)
        not_before :
            Restrict the token to uploading releases only after the given timestamp
            or tz-aware datetime. Must be used with ``not_after``.
        not_after :
            Restrict the token to uploading releases only before the given timestamp
            or tz-aware datetime. Must be used with ``not_before``.

        Raises
        ------
        exceptions.InvalidRestriction
            If the provided parameters cannot describe a valid description

        Returns
        -------
        `Token`
            The modified Token, to ease chaining calls.
        """
        for restriction in Restriction.restrictions_from_parameters(**kwargs):
            self._macaroon.add_first_party_caveat(restriction.dump_json())

        return self

    def dump(self) -> str:
        """
        Generates a string representing the token. This could be used for
        API authentication against PyPI.

        Returns
        -------
        str
            The token
        """
        return f"{self.prefix}-{self._macaroon.serialize()}"

    def check(self, key: str | bytes, project: str, now: int | None = None) -> None:
        """
        Raises pypitoken.ValidationError if the token is invalid.

        Parameters besides ``key`` will be used to provide the current context
        this token is used for, allowing to accept or reject the caveat restrictions.
        If a parameter is not passed, but a caveat using it is encountered, the
        caveat will not be met, the token will be found invalid, and this method
        will raise with an appropriate exception.

        Parameters
        ----------
        key : str
            Key of the macaroon, stored in PyPI database
        project : Optional[str], optional
            Normalized name of the project the bearer is attempting to upload to.

        Raises
        ------
        `pypitoken.ValidationError`
            Any error in validating the token will be raised as a ValidationError.
            The original exception (if any) will be attached
            as the exception cause (``raise from``).
        """
        verifier = pymacaroons.Verifier()

        context_kwargs: dict[str, Any] = {"project": project}
        if now:
            context_kwargs["now"] = now
        context = Context(**context_kwargs)

        errors: list[Exception] = []

        verifier.satisfy_general(
            functools.partial(self._check_caveat, context=context, errors=errors)
        )
        try:
            verifier.verify(self._macaroon, key)
        # https://github.com/ecordell/pymacaroons/issues/51
        except Exception as exc:
            if errors:
                # (we know it's actually a single item, there cannot be multiple items
                # in this list)
                (exc,) = errors

            raise exceptions.ValidationError(
                f"Error while validating token: {exc}"
            ) from exc

    @staticmethod
    def _check_caveat(caveat: str, context: Context, errors: list[Exception]) -> bool:
        """
        This method follows the pymacaroon Verifier.satisfy_general API, except
        that it takes a context parameter. It's expected to be used with
        `functools.partial`

        Parameters
        ----------
        caveat :
            raw caveat string that will be turned into a restriction to be checked
        context :
            Dict describing what we're trying to use the Token for, in order to decide
            whether the restrictions expressed by the caveat apply.
        errors :
            If any exception is raised, it will be appended to this list, so that
            we'll be able to raise them properly later

        Returns
        -------
        bool
            True if the caveat is met, False otherwise (should not raise).
        """

        try:
            restriction = Restriction.load_json(caveat=caveat)
        except exceptions.LoaderError as exc:
            errors.append(exc)
            return False

        try:
            restriction.check(context=context)
        except exceptions.ValidationError as exc:
            errors.append(exc)
            return False

        return True

    @property
    def restrictions(self) -> list[Restriction]:
        """
        Return a list of restrictions associated to this `Token`. This can be used
        to get a better insight on what this `Token` contains.

        Returns
        -------
        List[`Restriction`]

        Raises
        ------
        `pypitoken.LoaderError`
            When the existing restrictions cannot be parsed
        """
        return [
            Restriction.load_json(caveat=caveat.caveat_id)
            for caveat in self._macaroon.caveats
        ]


utils.replace_signature(
    method=Token.restrict, parameters=Restriction.restriction_parameters()
)
