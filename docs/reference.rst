API Reference
=============

Token
-----

.. autoclass:: pypitoken.Token
    :members: load, dump, restrict, create, domain, identifier, restrictions, check
    :member-order: bysource

Restriction classes
-------------------

You may come accross those classes, but while introspection is ok, you
should not have to call the methods directly. Use `Token.restrict` and
`Token.restrictions` instead.

.. autoclass:: pypitoken.restrictions.Restriction
    :members: load, load_json, dump_json, dump, check

.. autoclass:: pypitoken.DateRestriction
    :show-inheritance:

.. autoclass:: pypitoken.ProjectNamesRestriction
    :show-inheritance:

.. autoclass:: pypitoken.ProjectIDsRestriction
    :show-inheritance:

.. autoclass:: pypitoken.UserIDRestriction
    :show-inheritance:

.. autoclass:: pypitoken.LegacyNoopRestriction
    :show-inheritance:

.. autoclass:: pypitoken.LegacyProjectNamesRestriction
    :show-inheritance:

.. autoclass:: pypitoken.LegacyDateRestriction
    :show-inheritance:


Exceptions
----------

.. autoclass:: pypitoken.PyPITokenException
    :show-inheritance:

.. autoclass:: pypitoken.LoaderError
    :show-inheritance:

.. autoclass:: pypitoken.ValidationError
    :show-inheritance:

.. autoclass:: pypitoken.MissingContextError
    :show-inheritance:

.. autoclass:: pypitoken.InvalidRestriction
    :show-inheritance:
