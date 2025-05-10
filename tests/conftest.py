from __future__ import annotations

import pymacaroons
import pytest

from pypitoken import token


@pytest.fixture
def create_macaroon():
    def _(**kwargs):
        defaults = {
            "location": "example.com",
            "identifier": "123foo",
            "key": "ohsosecret",
            "version": pymacaroons.MACAROON_V2,
        }
        defaults.update(kwargs)
        return pymacaroons.Macaroon(**defaults)

    return _


@pytest.fixture
def create_token():
    def _(**kwargs):
        defaults = {
            "domain": "example.com",
            "identifier": "123foo",
            "key": "ohsosecret",
            "prefix": "pre",
        }
        defaults.update(kwargs)
        return token.Token.create(**defaults)

    return _
