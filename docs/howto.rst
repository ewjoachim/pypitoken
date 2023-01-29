=========
How to...
=========

This how-to section is divided into two parts: user and integrator doc.
User is for people who want to interact with their own tokens.
Integrator is for people interested into interacting this library in Warehouse.

"User" documentation: you're a PyPI user
========================================

Create a token for use in PyPI
------------------------------

As a user you can access your `PyPI account`__ and create a token, which you
can then load using `Token.load`. When creating a token, you can choose between
a user-wide and a project-scoped token. Whatever you decide, this library lets you
add additional restrictions to your token.

.. __: https://pypi.org/manage/account/

Regarding project-scoped tokens, PyPI only supports generating single project tokens.
Using this library you can take a user-scoped token and restrict it to multiple
projects, it will be usable on PyPI for a subset of your projects (see below).

Using this library, you can also create a token locally, but it will not be
registered in the PyPI Database, so you won't be able to use it to authenticate against
the PyPI API.

As of today, this library doesn't provide a way to create a working PyPI token
remotely (it's not an API client). Also, PyPI doesn't provide an API for generating
tokens, this has to be a manual operation.

Add restrictions to an existing token
-------------------------------------

Load your existing token::

    import pypitoken
    token = pypitoken.Token.load("pypi-...")

Add restrictions, for example restrict it to a given project::

    token.restrict(project_names=["sphinx"])

See `Token.restrict` for the list of possible restrictions.

Then dump the token::

    print(token.dump())

You can create multiple restrictions on a token, and all existing restrictions need to
be met in order to consider the token valid. This means you can create unusable tokens
by adding two incompatible restrictions (such as ``limited to project-a`` and then
``limited to project-b``).

You can add an upload restriction on a project you don't own, this won't give you
the ability to upload releases for this project. But if one day you're given upload
permissions on this project, then your token will start working.

This also mean that, using ``pypitoken``, you can create a project-scoped token for
a project that you haven't published yet. But don't wait too long, or someone else
may use the name before you had a chance to.

Remove restrictions from an existing token
------------------------------------------

Haha, well tried. The basis of Macaroons security is that you cannot remove
restrictions, only add new ones. Well, that is: if you don't have the Macaroon key.
If you have the Macaroon key, you can recreate a new Macaroon with the same key
and identifier and add whatever restrictions you want to it, including no restrictions.

You may wonder "where can I find my Macaroon key?", and the answer will be a bit
disappointing: you can't extract a Macaroon key from the macaroon itself. Theoretically,
if you're a PyPI admin, you can find the key which is stored in the PyPI Database.
Practically, PyPI admins don't go around looking at the token secrets keys. Your
Macaroon keys are safe where they are, and it's best for everyone this way.

Introspect a token's restrictions
---------------------------------

`Token.restrictions` will give you a list of restriction objects. These objects
are dataclass instances that you can compare and introspect easily.

There might also be cases where you want to interact with caveat values directly,
without a token. In this case, you can use the methods on the `Restriction` class::

    import pypitoken
    restriction = pypitoken.Restriction.load_json(
        '[0, 1234567891, 1234567890]'
    )
    # or
    restriction = pypitoken.Restriction.load(
        [0, 1234567891, 1234567890]
    )
    # DateRestriction()

    print(restriction.dump())  # outputs a dict
    print(restriction.dump_json())  # outputs a json-encoded string


"Integrator" documentation: you code for PyPI itself
====================================================

This part of the documentation is if you need to create and validate tokens.
The main user will be PyPI, but we could have the same kind of use-case
elsewhere.

Of course, just creating a macaroon with this library is not enough to have
it be valid on PyPI: valid macaroons need to exist in the database and this
library only handles the computation part, not the storing part.

Create a token
--------------

Use `Token.create`, `Token.restrict`, `Token.dump`:

.. code-block:: python

    import pypitoken
    token = pypitoken.Token.create(
        domain="pypi.org",
        identifier=database_macaroon.identifier,
        key=database_macaroon.secret_key,
        prefix="pypi",
    )

    # Restrict the projects that can be uploaded
    token.restrict(project_names=["project-normalized-name"])  # project-specific token
    # You can also restrict the token in time:
    token.restrict(not_before=timestamp_or_tz_aware_dt, not_after=timestamp_or_tz_aware_dt)
    # By project ID:
    token.restrict(project_ids=["00000000-0000-0000-0000-000000000000"])
    # And by user ID
    token.restrict(user_id="00000000-0000-0000-0000-000000000001")

    token_to_display = token.dump()

Check a token
-------------

Use `Token.load`, `Token.check`:

.. code-block:: python

    import pypitoken
    try:
        token = pypitoken.Token.load(raw="pypi-something")
    except pypitoken.LoaderError as exc:
        display_error(exc)
        return Http403()

    try:
        assert token.domain == "pypi.org", f"Token was generated for the wrong domain ('{token.domain}', expected 'pypi.org')"
        assert token.prefix == "pypi", f"Token has wrong prefix ('{token.prefix}', expected 'pypi')"
    except AssertionError as exc:
        display_error(exc)
        return Http403()

    try:
        # The project the user is currently uploading
        token.check(
            project_name="project-normalize-name",
            project_id="00000000-0000-0000-0000-000000000000",
            user_id="00000000-0000-0000-0000-000000000001",
            now=int(time.time()),
        )
    except pypitoken.ValidationError:
        display_error(exc)
        return Http403()


`ValidationError` and `LoaderError` should always come with an English readable
message, suitable for being shown to the user.

If you find a case where the exception is not as helpful as it should be, and you
believe the program has more information but it was lost during the exception bubbling
phase, or if the information in the exception is not appropriate to be shown back to the
user, this will be considered a ``pypitoken`` bug, feel free to open an issue.

You may omit the ``now`` parameter in the `Token.check` call, it will default
to the current integer timestamp. That said, it's ok to be explicit.

Version ``6.x`` upgrade
=======================

Version 6 marks major changes in the API of this module, following a complete
refactor of macaroons code withing PyPI itself.

Here is the list of things to be aware of:

Changes to legacy restrictions
------------------------------

- The pre-existing restriction classes have been renamed:

  - ``NoopRestriction`` became `LegacyNoopRestriction`

  - ``ProjectsRestriction`` became `LegacyProjectNamesRestriction`

    - Its parameter that was named ``projects`` is now named ``project_names``

  - ``DateRestriction`` became `LegacyDateRestriction`

- In order to create legacy restrictions from `Token.restrict`, one may now
  use:

  - ``legacy_noop=True`` instead of nothing for `LegacyNoopRestriction`

  - ``legacy_project_names`` instead of ``projects`` for `LegacyProjectNamesRestriction`

  - ``legacy_not_before`` and ``legacy_not_after``` instead of ``not_before``
    and ``not_after`` for `LegacyDateRestriction`

Addition of new restrictions
----------------------------

The following new restrictions have been added, that use the new format:

- `DateRestriction` (works the same as `LegacyDateRestriction`)
- `ProjectNamesRestriction` (works the same as `LegacyProjectNamesRestriction`)
- `ProjectIDsRestriction` (validates project ID in a list)
- `UserIDRestriction` (validates user ID)

Consequently, `Token.check` now accepts 2 new parameters:

- ``project_id``: a string representing the project ID
- ``user_id``: a string representing the uploading user ID

Other Changes
-------------

- `Token.check`: The documentation says:
     If a parameter is not passed, but a caveat using it is encountered, the
     caveat will not be met, the token will be found invalid, and this method
     will raise with an appropriate exception.

  This was actually not the case as ``project`` was a mandatory parameter.
  It's the case now: all perameters except ``key`` are now optional. Not providing
  one context parameter, but checking a restriction that uses this context parameter
  will result in a `MissingContextError`, which inherits `ValidationError`.
  There's a slight exception to this: as before, not providing the ``now``
  parameter will continue to mean we use the current timestamp as value.

- Internally, ``Restriction`` classes have been moved to ``pypitoken.restrictions``.
  This will not affect you if you import those classes from the ``pypitoken`` module
  directly (as you should) but some users load those classes from the internal
  module directly.
