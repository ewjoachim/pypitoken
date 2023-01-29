PyPIToken: Manipulate PyPI API tokens
=====================================

.. image:: https://img.shields.io/pypi/v/pypitoken?logo=pypi&logoColor=white
    :target: https://pypi.org/pypi/pypitoken
    :alt: Deployed to PyPI

.. image:: https://img.shields.io/pypi/pyversions/pypitoken?logo=pypi&logoColor=white
    :target: https://pypi.org/pypi/pypitoken
    :alt: Deployed to PyPI

.. image:: https://img.shields.io/github/stars/ewjoachim/pypitoken?logo=github
    :target: https://github.com/ewjoachim/pypitoken/
    :alt: GitHub Repository

.. image:: https://img.shields.io/github/actions/workflow/status/ewjoachim/pypitoken/ci.yml?logo=github
    :target: https://github.com/ewjoachim/pypitoken/actions?workflow=CI
    :alt: Continuous Integration

.. image:: https://img.shields.io/readthedocs/pypitoken?logo=read-the-docs&logoColor=white
    :target: http://pypitoken.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation

.. image:: https://img.shields.io/endpoint?logo=codecov&logoColor=white&url=https://raw.githubusercontent.com/wiki/ewjoachim/pypitoken/coverage-comment-badge.json
    :target: https://github.com/marketplace/actions/coverage-comment
    :alt: Coverage

.. image:: https://img.shields.io/github/license/ewjoachim/pypitoken?logo=open-source-initiative&logoColor=white
    :target: https://github.com/ewjoachim/pypitoken/blob/main/LICENSE
    :alt: MIT License

.. image:: https://img.shields.io/badge/Contributor%20Covenant-v1.4%20adopted-ff69b4.svg
    :target: https://github.com/ewjoachim/pypitoken/blob/main/CODE_OF_CONDUCT.md
    :alt: Contributor Covenant


PyPIToken is an open-source Python 3.7+ library for generating and manipulating
PyPI tokens.

PyPI tokens are very powerful, as that they are based on Macaroons_. They allow
the bearer to add additional restrictions to an existing token. For example, given
a PyPI token that can upload releases for any project of its owner, you can generate
a token that will only allow some projects, or even a single one.

.. _macaroons: https://en.wikipedia.org/wiki/Macaroons_(computer_science)

Here's an example:

.. code-block:: console

    $ pip install pypitoken

.. code-block:: python

    import pypitoken

    token = pypitoken.Token.load("pypi-foobartoken")

    print(token.restrictions)
    # [ProjectIDsRestriction(project_ids=["00000000-0000-0000-0000-000000000000"])]

    token.restrict(project_names=["requests"])

    print(token.restrictions)
    # [
    #     ProjectIDsRestriction(project_ids=["00000000-0000-0000-0000-000000000000"]),
    #     ProjectNamesRestriction(project_names=["requests"]),
    # ]

    token.dump()
    # pypi-newfoobartoken

This token we've created above will be restricted to uploading releases of ``requests``.
Of course, your PyPI user will still need to have upload permissions on ``requests``
for this to happen.

The aim of this library is to provide a simple toolbelt for manipulating PyPI tokens.
Ideally, someday, PyPI (Warehouse_) itself may generate their tokens using this
library too. This should make it easier to iterate on new kinds of restrictions for
PyPI tokens, such as those discussed in the `original implementation issue`__.

.. _Warehouse: https://github.com/pypa/warehouse/
.. __: https://github.com/pypa/warehouse/issues/994

A discussion for integrating this library to the Warehouse environment is ongoing:

- In the `Python Packaging discussions`_ for putting the project under the PyPA umbrella
- In the `Warehouse tracker`_ for replacing the current macaroon implementation with
  this lib

.. _`Python Packaging discussions`: https://discuss.python.org/t/pypitoken-a-library-for-generating-and-manipulating-pypi-tokens/7572
.. _`Warehouse tracker`: https://github.com/pypa/warehouse/issues/9184

.. Below this line is content specific to the README that will not appear in the doc.
.. end-of-index-doc

Where to go from here
---------------------

The complete docs_ is probably the best place to learn about the project.

If you encounter a bug, or want to get in touch, you're always welcome to open a
ticket_.

.. _docs: http://pypitoken.readthedocs.io/en/latest
.. _ticket: https://github.com/ewjoachim/pypitoken/issues/new
