from typing import Optional
from dotenv import dotenv_values
from pydantic import validate_call
from errors import TheiaCredentialsError

from api import TheiaAPI

config = {
    **dotenv_values(".env.shared"),  # load shared development variables
    **dotenv_values(".env.secret"),  # load sensitive variables
}


@validate_call(validate_return=True)
def get_api(username: Optional[str] = None, password: Optional[str] = None) -> TheiaAPI:
    """
    Creates a `TheiaAPI` object and returns it.

    Parameters
    ----------
    username: Optional[str]
        The username of the user's USGS account.
    password: Optional[str]
        The password of the user's USGS account.

    Returns
    -------
    api: TheiaAPI
        A `TheiaAPI` object created with the user's credentials.

    Raises
    ------
    TheiaCredentialsError
        When username and password are not set in config and not provided in the method.
    """
    if config["USERNAME"] == "None" or config["PASSWORD"] == "None":
        if username is None or password is None:
            raise TheiaCredentialsError(
                "Both Username and Password are required. Please set username and "
                "password in config through the `set_credentials` function or provide "
                "one in the `get_api` function."
            )
        config["USERNAME"] = username
        config["PASSWORD"] = password

    assert config["USERNAME"] is not None
    assert config["PASSWORD"] is not None

    api = TheiaAPI(username=config["USERNAME"], password=config["PASSWORD"])
    return api


@validate_call(validate_return=True)
def set_credentials(username: str, password: str) -> None:
    """
    Sets user credentials in the config file.

    Parameters
    ----------
    username: str
        The username of the user's USGS account.
    password: str
        The password of the user's USGS account.
    """
    pass
