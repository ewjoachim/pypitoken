from . import exceptions, token


def get_token_from_pypirc(
    repository: str = "pypi", path: str = "~/.pypirc"
) -> token.Token:
    try:
        from twine.utils import get_config, get_userpass_value
    except ImportError:
        raise RuntimeError(
            "Twine is required for this function. "
            "Please reinstall pypitokens with extra 'twine'."
        )
    try:
        config = get_config(path=path)[repository]
    except KeyError:
        raise exceptions.LoadError(f"Missing section {repository} in {path}")
    password = get_userpass_value(cli_value=None, config=config, key="password")
    if not password:
        raise exceptions.LoadError(f"Twine could not read password from {path}")

    return token.Token.load(password)
