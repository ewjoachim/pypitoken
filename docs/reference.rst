API Reference
=============

Token
-----

.. autoclass:: pypitoken.Token
    :members: load, dump, derive, create, domain, identifier, restrictions, check
    :member-order: bysource

Restriction classes
-------------------

You may come accross those classes, but while introspection is ok, you
should not have to call the methods directly. Use `Token.derive` and
`Token.restrictions` instead.

.. autoclass:: pypitoken.NoopRestriction
    :exclude-members: get_schema

.. autoclass:: pypitoken.ProjectsRestriction
    :exclude-members: get_schema
