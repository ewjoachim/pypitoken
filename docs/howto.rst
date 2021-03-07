How to...
=========

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

    token.derive(projects=["sphinx"])

See `Token.derive` for the list of possible restrictions.

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
