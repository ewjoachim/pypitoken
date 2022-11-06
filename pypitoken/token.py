from __future__ import annotations

import datetime
import functools

import pymacaroons
from typing_extensions import ParamSpec

from pypitoken import exceptions, restrictions

PREFIX = "pypi"

P = ParamSpec("P")


class Token:
    """
    Create a `Token` (as PyPI itself would do), load an existing
    `Token`, create additional restrictions on a `Token` and dump a `Token` string
    from a `Token`.

    This class is an higher level abstraction over the Macaroons from pymacaroons,
    with specific knowledge of their implementation within PyPI.

    Attributes
    ----------
    prefix : ``str``
        PyPI tokens are usually prefixed with ``pypi``, but this is arbitrary
    domain : ``str``
        PyPI tokens are attached to a specific domain, usually ``pypi.org`` or
        ``test.pypi.org``
    identifier : ``str``
        This part is how PyPI will find a token in its database and associate it to a
        specific user. Even when additional restrictions are added to a token, the
        identifier will still be readable in the token. While this is not exactly
        a secret part of the token, it's best to keep it reasonably private.
    _macaroon : ``pymacarrons.Macaroon``
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

    def restrict(
        self,
        not_before: int | datetime.datetime | None = None,
        not_after: int | datetime.datetime | None = None,
        project_names: list[str] | None = None,
        project_ids: list[str] | None = None,
        user_id: str | None = None,
        # Legacy params
        legacy_project_names: list[str] | None = None,
        legacy_not_before: int | datetime.datetime | None = None,
        legacy_not_after: int | datetime.datetime | None = None,
        legacy_noop: bool | None = None,
    ) -> Token:
        """
        Modifies the token in-place to add restrictions to it. This can be called by
        PyPI as well as by anyone, adding restrictions to new or existing tokens.

        Multiple restrictions of different types can be added in one call to
        `restrict()`. Alternatively, multiple restrictions of the same type can be added
        via multiple calls to `restrict()`.

        Note: a token allows the owner to delegate their rights to the bearer.
        Consequently, a token adding restrictions linked to a project that the owner
        cannot use will not make its bearer able to upload releases to the project. As
        stated in the name, restrictions can reduce the scope of a token, and cannot
        broaden it. It's possible to create a token that can do nothing, for example by
        adding two incompatible restrictions.

        Parameters
        ----------

        not_before :
            Restrict the token to uploading releases only after the given timestamp or
            tz-aware datetime. Must be used with ``not_after``. By default, None (no
            restriction)
        not_after :
            Restrict the token to uploading releases only before the given timestamp or
            tz-aware datetime. Must be used with ``not_before``. By default, None (no
            restriction)
        project_names :
            Restrict the token to uploading releases only for projects with these names,
            by default None (no restriction)
        project_ids :
            Restrict the token to uploading releases only for projects with these ids,
            by default None (no restriction)
        user_ids :
            Restrict the token to uploading user attempting to upload Restrict the token
            to being used only by user with this id, by default None (no restriction)
        legacy_not_before :
            Uses the legacy restriction format (results in longer token size). Restrict
            the token to uploading releases only after the given timestamp or tz-aware
            datetime. Must be used with ``not_after``. By default, None (no restriction)
        legacy_not_after :
            Uses the legacy restriction format (results in longer token size). Restrict
            the token to uploading releases only before the given timestamp or tz-aware
            datetime. Must be used with ``not_before``. By default, None (no
            restriction)
        legacy_project_names :
            Uses the legacy restriction format (results in longer token size). Restrict
            the token to uploading releases only for projects with these ed name of the
            project the bearer is attempting to upload toed names, by default None (no
            restriction)
        legacy_noop :
            Uses the legacy restriction format (results in longer token size). user
            attempting to upload This restriction being there or not doesn't change the
            validity of the token.

        Raises
        ------
        exceptions.Invalidrestrictions.Restriction
            If the provided parameters cannot describe a valid description

        Returns
        -------
        `Token`
            The modified Token, to ease chaining calls.
        """
        for restriction in restrictions.Restriction.restrictions_from_parameters(
            not_before=not_before,
            not_after=not_after,
            project_names=project_names,
            project_ids=project_ids,
            user_id=user_id,
            legacy_project_names=legacy_project_names,
            legacy_not_before=legacy_not_before,
            legacy_not_after=legacy_not_after,
            legacy_noop=legacy_noop,
        ):
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

    def check(
        self,
        key: str | bytes,
        project_name: str | None = None,
        project_id: str | None = None,
        user_id: str | None = None,
        now: int | datetime.datetime | None = None,
    ) -> None:
        """
        Raises pypitoken.ValidationError if the token is invalid.

        Parameters besides ``key`` are all optional and will be used to provide the
        current context this token is used for, allowing to accept or reject the caveat
        restrictions. If a parameter is not passed, but a caveat using it is
        encountered, the caveat will not be met, the token will be found invalid, and
        this method will raise with an appropriate exception. There is an exception for
        ``now``: if not passed, it defaults to the current timestamp.

        Parameters
        ----------
        key : str
            Key of the macaroon, stored in PyPI database
        project_name :
            Normalized name of the project the bearer is attempting to upload to
        project_id :
            ID of the project the bearer is attempting to upload to
        user_id :
            ID of the user attempting to upload
        now :
            Timestamp of the moment the upload takes place, or tz-aware datetime.
            Defaults to the current timestamp.

        Raises
        ------
        `pypitoken.ValidationError`
            Any error in validating the token will be raised as a ValidationError. The
            original exception (if any) will be attached as the exception cause (``raise
            from``).
        """
        verifier = pymacaroons.Verifier()

        context = restrictions.Context(
            project_name=project_name,
            project_id=project_id,
            user_id=user_id,
            now=now,
        )

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
    def _check_caveat(
        caveat: str,
        context: restrictions.Context,
        errors: list[Exception],
    ) -> bool:
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
            restriction = restrictions.Restriction.load_json(caveat=caveat)
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
    def restrictions(self) -> list[restrictions.Restriction]:
        """
        Return a list of restrictions associated to this `Token`. This can be used
        to get a better insight on what this `Token` contains.

        Returns
        -------
        List[`restrictions.Restriction`]

        Raises
        ------
        `pypitoken.LoaderError`
            When the existing restrictions cannot be parsed
        """
        return [
            restrictions.Restriction.load_json(caveat=caveat.caveat_id)
            for caveat in self._macaroon.caveats
        ]
