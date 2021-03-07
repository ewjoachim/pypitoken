import dataclasses
import functools
import json
from typing import Dict, List, Optional, Type, TypeVar

import jsonschema
import pymacaroons

from pypitoken import exceptions

PREFIX = "pypi"

T = TypeVar("T", bound="Restriction")


# Making the class a dataclass is meanly meant to ease comparison using ==
@dataclasses.dataclass
class Restriction:
    def dump(self) -> str:
        return json.dumps(self.dump_value())

    @staticmethod
    def get_schema() -> Dict:
        """
        Return a jsonschema Dict object used to validate the format
        of a json restriction.
        """
        raise NotImplementedError

    @classmethod
    def validate_value(cls, value: Dict) -> None:
        try:
            jsonschema.validate(
                instance=value,
                schema=cls.get_schema(),
            )
        except jsonschema.ValidationError as exc:
            raise exceptions.ValidationError() from exc

    @classmethod
    def load_from_value(cls: Type[T], value: Dict) -> T:
        raise NotImplementedError

    def check(self, context) -> None:
        raise NotImplementedError

    def dump_value(self) -> Dict:
        raise NotImplementedError


@dataclasses.dataclass
class NoopRestriction(Restriction):
    """
    Says it restricts the `Token`, but doesn't actually restrict it.
    """

    @staticmethod
    def get_schema() -> Dict:
        return {
            "type": "object",
            "properties": {
                "version": {"type": "integer", "const": 1},
                "permissions": {"type": "string", "const": "user"},
            },
            "required": ["version", "permissions"],
        }

    @classmethod
    def load_from_value(cls, value: Dict) -> "NoopRestriction":
        return cls()

    def check(self, context: Dict) -> None:
        # Always passes
        return

    def dump_value(self) -> Dict:
        return {"version": 1, "permissions": "user"}


@dataclasses.dataclass
class ProjectsRestriction(Restriction):
    """
    Restrict a `Token` to uploading releases for a specific set of packages.

    Attributes
    ----------
    projects :
        Normalized project names this token may upload to.
    """

    projects: List[str]

    @staticmethod
    def get_schema() -> Dict:
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
                },
            },
            "required": ["version", "permissions"],
        }

    @classmethod
    def load_from_value(cls, value: Dict) -> "ProjectsRestriction":
        projects = value["permissions"]["projects"]
        return cls(projects=projects)

    def dump_value(self) -> Dict:
        return {"version": 1, "permissions": {"projects": self.projects}}

    def check(self, context: Dict) -> None:
        try:
            project = context["project"]
        except KeyError:
            raise exceptions.MissingContextError(
                "Missing key 'project' from validation context"
            )

        if project not in self.projects:
            raise exceptions.ValidationError(
                f"This token can only be used for project(s): "
                f"{', '.join(self.projects)}. Received: {project}"
            )


# We could use __subclasses__ but that could lead to all kinds of funky things,
# especially in a security-sensistive library
RESTRICTION_CLASSES: List[Type[Restriction]] = [NoopRestriction, ProjectsRestriction]


def json_load_caveat(caveat: str) -> Dict:
    try:
        value = json.loads(caveat)
    except Exception as exc:
        raise exceptions.LoadError(f"Error while loading caveat: {exc}") from exc

    if not isinstance(value, dict):
        raise exceptions.LoadError(
            f"Caveat is a well-formed JSON string but not a dict: {value}"
        )

    return value


def load_restriction(
    caveat: str, classes: List[Type[Restriction]] = RESTRICTION_CLASSES
) -> "Restriction":
    """
    Create a Restriction from a caveat restriction string.

    Raises
    ------
    pypitokens.LoadError
        If the format cannot be understood

    Returns
    -------
    [type]
        [description]
    """
    value = json_load_caveat(caveat=caveat)
    for subclass in classes:
        try:
            subclass.validate_value(value)
        except exceptions.ValidationError:
            continue
        return subclass.load_from_value(value)

    raise exceptions.LoadError(f"Could not find matching Restriction for {value}")


def check_caveat(caveat: str, context: Dict) -> bool:
    """
    This function follows the pymacaroon Verifier.satisfy_general API, except
    that it takes a context parameter. It's expected to be used with `functools.partial`

    Parameters
    ----------
    caveat : str
        raw caveat string that will be turned into a restriction to be checked
    context :
        Dict describing what we're trying to use the Token for, in order to decide
        whether the restrictions expressed by the caveat apply.

    Returns
    -------
    bool
        True if the caveat is met, False otherwise (should not raise).
    """
    try:
        restriction = load_restriction(caveat=caveat)
    except exceptions.LoadError:
        return False

    try:
        restriction.check(context=context)
    # Actually, the pymacaroons API tells us to return False when a validation fail,
    # which keeps us from raising a more expressive error.
    # Hopefully, this will be adressed in pymacaroons in the future.
    except exceptions.PyPITokenException:
        return False

    return True


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
    def load(cls, raw: str) -> "Token":
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
        pypitoken.LoadError
            Raised if the token cannot be loaded
        """
        try:
            prefix, raw_macaroon = raw.split("-", maxsplit=1)
        except ValueError:
            raise exceptions.LoadError("Token is missing a prefix")
        try:
            macaroon = pymacaroons.Macaroon.deserialize(raw_macaroon)
        except Exception as exc:
            raise exceptions.LoadError(f"Deserialization error: {exc}") from exc
        return cls(
            prefix=prefix,
            macaroon=macaroon,
        )

    @classmethod
    def create(
        cls,
        domain: str,
        identifier: str,
        key: str,
        prefix: str = PREFIX,
        version: int = pymacaroons.MACAROON_V2,
    ) -> "Token":
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
        Token
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

    def restrict(
        self,
        projects: Optional[List[str]] = None,
    ) -> "Token":
        """
        Modifies the token in-place to add restrictions to it.
        This can be called by PyPI as well as by anyone, adding restrictions to
        new or existing tokens.

        Note that if no restriction is added, this method will still add a noop
        restriction, to match the original implementation.

        Note: a token allows the owner to delegate their rights to the bearer.
        Consequently, a token adding restrictions linked to a project that the owner
        cannot use will not make its bearer able to upload releases to the project.
        As stated in the name, restrictions can reduce the scope of a token, and
        cannot broaden it. It's possible to create a token that can do nothing,
        for example by adding two incompatible restrictions.

        Parameters
        ----------
        projects :
            Restrict the token to uploading releases only for projects with these
            normalized names, by default None (no restriction)

        Returns
        -------
        Token
            The modified Token, to ease chaining calls.
        """
        caveats: List[str] = []
        if projects is not None:
            caveats.append(ProjectsRestriction(projects).dump())

        # Add other restrictions here

        if not self._macaroon.caveats and not caveats:
            # It's actually not really useful to add a noop restriction, but
            # it's done that way in the original implementation, and has been kept so
            # far
            caveats = [NoopRestriction().dump()]

        for caveat in caveats:
            self._macaroon.add_first_party_caveat(caveat)

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

    def check(
        self,
        key: str,
        project: Optional[str] = None,
    ) -> None:
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
            Name of the project the bearer is attempting to interact with, by default
            None
        filename : Optional[str], optional
            Name of the file the bearer is attempting to upload, by default None
        hash : Optional[str], optional
            [description], by default None
        timestamp : Optional[datetime.datetime], optional
            [description], by default None

        Raises
        ------
        pypitoken.ValidationError
            Any error in validating the token will be raised as a ValidationError.
            The error message should be an English human-readable string appropriate
            to display to the user. The original exception (if any) will be attached
            as the exception cause (``raise from``).
        """
        verifier = pymacaroons.Verifier()

        context = {"project": project}

        verifier.satisfy_general(functools.partial(check_caveat, context=context))
        try:
            verifier.verify(self._macaroon, key)
        except Exception as exc:
            # https://github.com/ecordell/pymacaroons/issues/51
            raise exceptions.ValidationError(
                f"Error while validating token: {exc}"
            ) from exc

    @property
    def restrictions(self) -> List[Restriction]:
        """
        Return a list of restrictions associated to this `Token`. This can be used
        to get a better insight on what this `Token` contains.

        Returns
        -------
        List[Restriction]
        """
        return [
            load_restriction(caveat=caveat.caveat_id)
            for caveat in self._macaroon.caveats
        ]
