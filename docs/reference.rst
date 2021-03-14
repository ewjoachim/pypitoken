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

.. autoclass:: pypitoken.token.Restriction

.. autoclass:: pypitoken.NoopRestriction
    :show-inheritance:

.. autoclass:: pypitoken.ProjectsRestriction
    :show-inheritance:


Exceptions
----------

.. autoclass:: pypitoken.PyPITokenException
    :show-inheritance:

.. autoclass:: pypitoken.LoaderError
    :show-inheritance:

.. autoclass:: pypitoken.ValidationError
    :show-inheritance:
