Discussions
===========

So PyPI tokens are based on Macaroons.

What is a macaroon, how does it work, how is it secure?
-------------------------------------------------------

At heart, a macaroon is an introspectable token, it lets its bearer be identified.
There's an identifier, which is readable in the token, and a secret key which is
not included in the macaroon.
A HMAC_ hash of the identifier and the secret key is also present in the token.
This results in the following properties:

- Given a macaroon, you can extract the identifier easily
- If you know the identifier and the key, you can check that the macaroon has not
  been modified
- Given just the macaroon, you cannot extract the key. The key is the secret part that
  lets you generate and check a macaroon's authenticity.

But then the power of the macaroon comes from the following: you can add caveats to
the macaroon. A caveat is a readable string. When you add a caveat, you take the
previous ``HMAC``, and use it as a key for a new HMAC of the caveat. This gives you
the following properties:

- Given a macaroon, you can still extract the identifier and the caveat strings
- Given a macaroon and its key, you can check each step by computing the same ``HMAC``
  on your side and check that your hash is still consistent
- Given a macaroon, anyone can add a caveat
- Given a macaroon without the key, it's impossible to remove a caveat. Intermediate
  hashes are discarded each time you add a caveat, so the only way is forward (adding
  more caveats).

The specification doesn't say what the caveat strings should be, but the idea is that
each caveat is adding a restriction to the original macaroon, so that when the bearer
has to send the macaroon, they only delegate the smallest fraction of their power.

It's up to the Macaroon original minter to decide how to understand the caveats,
but when they receive a macaroon for

.. _HMAC: https://en.wikipedia.org/wiki/HMAC

How are macaroons implemented in this library?
----------------------------------------------

TL;DR: they're not :D This library is a abstraction over PyMacaroons_, but with a
specialization on the needs of PyPI. Here are a few things this library does:

- Distinguish between ``tokens`` and ``macaroons``. PyPI tokens have a ``pypi-`` prefix.
  A token is a serialized macaroon with a prefix.
- Rename caveats "restrictions". The word caveat is nice and latin and all, but as
  far as the author can tell, in international contexts, people tend not to understand
  immediately what "caveat" mean in this context. Given the idea of this lib is to
  ease the use of PyPI tokens, where those caveats are mainly used as restrictions,
  it felt more logical to name it this way.

.. _PyMacaroons: https://github.com/ecordell/pymacaroons

How are macaroons implemented in PyPI?
--------------------------------------

PyPI keeps a database table of macaroons, with identifiers, keys, and related users.
When a macaroon bearer uploads a release using their macaroon, the identifier is read,
then from the database, the key and user are extracted. The macaroon is checked using
the key and caveats are checked against the upload information. If the macaroon is
valid, then PyPI checks if the user has upload rights on the package, and then proceeds.

The caveats are json-encoded strings, and as of March 2021, they come in 2 flavors:

- ``"{"version": 1, "permissions": "user"}"`` (note: it's the string ``"user"`` here,
  not a placeholder for the username), which is always met. It's represented in this
  library by the class `NoopRestriction`,
- ``"{"version": 1, "permissions": {"projects": ["<project name>", ...]}}"`` (note:
  ``"<project name>"`` is a placeholder here). It's met if the project we upload
  is among the ones listed in the caveats. It's represented by the
  `ProjectsRestriction`.

The projects restriction that PyPI implements is limited to:

- a single project per token (even if the restriction format allows multiple projects)
- creating tokens for existing projects you own (even though it's perfectly possible
  to create tokens for projects that don't exist yet, or for which you don't have
  upload permission yet).

.. note::

    You still need to be a project maintainer or owner for your tokens to work on a
    project. Restrictions can only reduce the scope of a token.

Do we really need an abstraction layer over PyMacaroons?
--------------------------------------------------------

Yes ? No ? Maybe ? What's clear is that the implementation in PyPI is adding some
unnecessary complexity, and the community would benefit from a single source of
macaroons, so that the same codebase will be responsible for serializing and
deserializing the custom PyPI token restrictions.

Can we add new restrictions?
----------------------------

As long as PyPI doesn't use ``pypitoken`` to generate tokens, it's not very useful
to implement new restrictions. But once we get it merged, then we'll want to add plenty
of new and smart restrictions (based on time, upload file name and hash, etc)

The restrictions planned for the future are:

- Version-based restriction
- Filename-based restriction
- Hash-sum-based restriction
- Time-window-based restriction
- IP-based restriction
- One-time-use restriction (this will require Warehouse to remember a value)
- Somehow restricting to uploads coming from a given project's CI
- ...? (ideas welcome)

Most of those were initially discussed in the `Warehouse tracker`__.

.. __: https://github.com/pypa/warehouse/issues/994

There would be 2 main categories of restrictions:

- Restrictions you apply just before uploading a release to limit the possible
  consequences of token steal or replay attack,
- Restrictions you apply before handing your token over to a third party, to ensure
  they can't mis-use it.

Is this library a part of PyPI?
-------------------------------

It's being developper externally. The initiator of this project is a member of the
Python Packaging Authority (PyPA) and PyPI moderator, but not an admin nor a committer.

As of today, the library is not part of the PyPA. Once this lib is done, it's planned
to apply for this lib to be added to PyPA.

.. _Macaroon recipe:

Why is there a noop restriction?
--------------------------------

Good question. The author is not sure either. In the original discussions in Warehouse,
the idea was to have 2 types of tokens: "user" tokens and "projects" tokens. But even
without restrictions, tokens are already scoped to a specific user, so adding a "user"
restriction actually changes nothing, thus why it's implemented in ``pypitoken`` as a
`NoopRestriction`.

Though it's not been tested yet, tokens without restrictions should work the same
as tokens with a noop restriction (or, for what it's worth, token with multiple noop
restrictions).

Should we have multiple restrictions in a single caveat?
--------------------------------------------------------

This is a real question we may encounter when we'll have multiple types of restrictions:
when we want to apply a restriction to multiple aspects, should we implement all of them
in a single caveat modelling all the aspects, or should each restriction be its own
caveat?

It can be noted that "user" (noop) restrictions and "projects" restrictions are not
compatible, so this would tend to indicate it was not planned for multiple restrictions
to be grouped into a single caveat.

Having multiple restrictions in a single json payload makes it harder to check whether
it's valid or not (at least, while the general format of the json payloads is not
unified). No definitive answer is given at this time.

What does "normalized name" mean?
---------------------------------

Throughout the doc, the term "normalized name" for a project is regularily used.
This is because some characters are synonymous in a project name, so in order to match
a project name, we need to put it to canonical form first.

See `PEP 503`__ for all the details.

.. __: https://www.python.org/dev/peps/pep-0503/#normalized-names

What would be good practice regarding token restrictions and traceability
-------------------------------------------------------------------------

PyPI offers quite a bit of interesting features regarding token traceability & audit:
- You can list your existing tokens, including a description of your choice
- You can revoke them
- You can see the restrictions applied at generation time by PyPI
- Other project admins can see if you generated tokens for projects you share with them

It's generally considered a good idea to use each token for one dedicated usage, so that
if you need to revoke a token, you don't break anything else.

Adding restrictions yourself on existing tokens have consequences on those elements:

- If two tokens are created by adding restrictions to a single "parent" token, revoking
  the parent token will revoke all the children at the same time. Given it's still a
  good idea to use a token for one usage only, when you generate a token with a
  restriction, if you plan to store the child token, then you should consider throwing
  away immediately the original token. Of course, this is not always applicable, some
  use-cases may require to store both but you may need to track the diffusion of your
  tokens yourself.
- In PyPI, restrictions you added yourself will not appear in the token list, so
  it's a good idea to be overly explicit in the token description. Note that the
  description field cannot be modified after generation.

This way, your PyPI account page will still be a good place to track all of your
existing tokens, and you will be able to follow each of them easily.

All this talking about Macaroons, I'm hungry now!
-------------------------------------------------

Here's a recipe for Montmorillon Macaroons, as done in the author's region.
Note that it's using SI units.

Ingredients:

- Sugar: 125g
- Ground almonds: 150g
- Egg white: 70g (that's 2 eggs)
- Bitter almond (few drops)

Steps:

1. Preheat oven to 50°C.
2. Spread the gound almonds on a baking sheet, put in oven for 10 to 15 minutes.
3. Remove it from oven, let it cool and mix with sugar.
4. Whip the egg whites stiff and add a few drops of bitter almond.
5. Using a rubber spatula, fold the egg whites into the sugar & almond batter.
6. Pour the batter into a piping bag with a ribbed nozzle.
7. Form the macaroons on baking paper and leave them to rest for 2h at ambiant
   temperature.
8. Preheat oven to 190°C.
9. Lower the oven to 180°C, and put the macaroons in for 3 minutes, then 15 minutes at
   160°C.
10. Allow to cool before yummy time.

Nice logo! Where did you get it?
--------------------------------

Design is "macaroon" by Izwar Muis from the Noun Project.
Colors are taken from Python's visual identity.
