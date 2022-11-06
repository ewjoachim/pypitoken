Tutorial
========

In this section, we're going to build together a small script showcasing
PyPIToken and its everyday use.

Our objective is to create a small python script that will read a user-wide PyPI
token, a created a new token derived from it, restricted to a single project.

Along the way, we'll create an empty project and upload it on `Test PyPI`_.


Prerequisites & installation
----------------------------

You will need a virtual environment (or ``virtualenv``). If you're not use to creating
one, please have a look a the virtualenv_ Python Packaging official documentation.

.. _virtualenv: https://packaging.python.org/tutorials/installing-packages/#creating-virtual-environments

Once your virtualenv is created, let's install ``pypitoken``

.. code-block:: console

    (venv) $ pip install pypitoken build twine

.. note::

    How to read code examples as above? The ``$`` tells you that you are in a shell
    (a bash shell, not a Python shell), the ``(venv)`` prefix tells you that your
    ``virtualenv`` should be activated, probably with the ``source .../bin/activate``
    line that the ``virtualenv`` tutorial above covered. So you can type or copy-paste
    starting from ``pip``.

A bit of boilerplate
--------------------

We'll do this in a single file. Let's create a file named ``tutorial.py`` and type
the following::

    import sys

    def add_restriction(raw_token: str, project: str) -> str:
        # TODO
        return raw_token

    def main():
        raw_token = sys.stdin.read().strip()
        try:
            project = sys.argv[1]
        except IndexError:
            sys.exit(f"Usage: {sys.argv[0]} {{project_name}} < token")

        print(add_restriction(raw_token=raw_token, project=project))

    if __name__ == "__main__":
        main()

So we have our main function, that reads tokens from standard input and command-line,
adds a restriction (not actually implemented yet) and then print it back.

Let's try the boilerplate on a fake token:

.. code-block:: console

    (venv) $ echo "hello" | python tutorial.py myproject
    hello

(We're writing ``hello`` to the standard output and piping__ that to our script, which
prints back ``hello``.)

.. __: https://en.wikipedia.org/wiki/Pipeline_(Unix)

Preparing our token
-------------------

We're going to use your `Test PyPI`_ account, so you can start by `creating one`__ if
you don't have one already.

.. _`Test PyPI`: https://test.pypi.org/
.. __: https://test.pypi.org/account/register/

Create a user-wide token from your `account page`__, and copy it.

.. __: https://test.pypi.org/manage/account/

We'll save the password to an environment variable, so we can get it back later:

.. code-block:: console

    (venv) $ export TOKEN=< your token starting with pypi- >

In you shell, export the following environment variables, this will make ``twine`` able
to use your token:

.. code-block:: console

    (venv) $ export TWINE_REPOSITORY=testpypi
    (venv) $ export TWINE_USERNAME=__token__
    (venv) $ export TWINE_PASSWORD=$TOKEN

.. warning::

    Don't put spaces around the equal sign. Bash is touchy with spaces.

Creating a project to upload
----------------------------

Our project name will be ``test-<your-username>-<today as yyyy-mm-dd>``. For readability
sake, we'll be using a specific username and date throughout the documentation, but
remember to always swap with your own project name and date.

We'll create an empty project just for the sake of testing the upload procedure.
In a file named ``setup.py``, type the following::

    from setuptools import setup

    setup(name="test-ewjoachim-2021-03-07", version="0.0.0")

Now let's upload the package to Test PyPI:

.. code-block:: console

    (venv) $ python -m build
    (venv) $ twine upload dist/*

Your package should be uploaded at version 0.0.0. The ``twine upload`` command output
should end with a link to your package:

.. code-block:: text

    View at:
    https://test.pypi.org/project/test-ewjoachim-2021-03-07/0.0.0/

Add a restriction
-----------------

Now let's implement our ``add_restriction`` function in ``tutorial.py``::

    from pypitoken import Token

    def add_restriction(raw_token: str, project: str) -> str:
        token = Token.load(raw_token)
        print("Original restrictions:", token.restrictions, file=sys.stderr)

        token.restrict(project_names=[project])
        print("New restrictions:", token.restrictions, file=sys.stderr)

        return token.dump()

Going line by line:

- ``token = Token.load(raw_token)`` loads the token in string form into an object.
  An exception might be raised here, of the type `pypitoken.LoaderError`.
- ``print(...)``: This is a debug step, that will show us the
  restrictions our token contains. When called the second time, it should contain
  our new restriction.
- ``token.restrict(project_names=[project])`` adds new restrictions to our
  token. Here, we're using the ``projects`` keywords which expects a list of
  projects, but we only have a single project to pass, so we make a list with a
  single object.
- ``return token.dump()``: Then we turn our modified token back int a string
  and return it.

Test it
-------

We're going to make a new test, calling again:

.. code-block:: console

    (venv) $ echo $TOKEN | python tutorial.py test-ewjoachim-2021-03-07

This time we should see our token getting a new restriction.
Let's see if it still works:

.. code-block:: console

    (venv) $ export TWINE_PASSWORD=$(echo $TOKEN | python tutorial.py test-ewjoachim-2021-03-07)
    (venv) $ twine upload dist/*

This should have worked. Now let's make another token that should be rejected:

.. code-block:: console

    (venv) $ export TWINE_PASSWORD=$(echo $TOKEN | python tutorial.py some-other-project)
    (venv) $ twine upload dist/*

This time you should have received an error. There are 3 reasons why it's logical to
have an error here:

- The project ``some-other-project-foo-bar`` does not exist
- You consequently don't have upload permissions on it
- Even if you had, your token is restricted to a different project.

Thankfully, the error message is explicit in that the third error is the first one that
was encountered. Of course, if you want to create a new package on Test PyPI, so that
you can eleminate the two other causes, feel free, but this tutorial doesn't cover this.

Looking back
------------

Pfew! Let's take a moment to summarize what we've done:

- Created a project on Test PyPI
- Had Test PyPI generate a token for us. The token can upload releases for any of our
  projects on Test PyPI
- Then we locally added a restriction on the token, so that it's now bound to only
  one of our projects
- And then we checked that this new token still works for that project, and refuses to
  upload to other projects.
- Oh, and we created this as a generic command-line tool that can be used to add
  restrictions to real PyPI tokens too!

That was a nice journey. Time for a cup of tea, and maybe a
:ref:`Macaroon <Macaroon recipe>`.

Going further
-------------

To continue with practical steps, head to the "`howto`" section.

If you want to better understand some design decisions, head to the `Discussions
<discussions>` section.
