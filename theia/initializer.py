from typing import Optional
from dotenv import dotenv_values, load_dotenv, set_key
import os
from pathlib import Path
from pydantic import validate_call
from errors import TheiaCredentialsError

from api import TheiaAPI


@validate_call(validate_return=True)
def get_api(
    username: Optional[str] = None,
    password: Optional[str] = None,
    dotenv_path: Optional[str] = None,
) -> TheiaAPI:
    """
    Creates a `TheiaAPI` object and returns it.

    Parameters
    ----------
    username: Optional[str]
        The username of the user's USGS account.
    password: Optional[str]
        The password of the user's USGS account.
    dotenv_path: Optional[str]
        Path to the dotenv file to read credentials from. If provided, it overrides any other provided credentials.

    Returns
    -------
    api: TheiaAPI
        A `TheiaAPI` object created with the user's credentials.

    Raises
    ------
    TheiaCredentialsError
        When username and password are not set in config and not provided in the method.
    """

    if dotenv_path:
        load_dotenv(dotenv_path=dotenv_path)
        username = os.getenv("USERNAME")
        password = os.getenv("PASSWORD")

    if not username or not password:
        raise TheiaCredentialsError(
            "Both Username and Password are required. Please set username and password in "
            "the dotenv file, in config, or provide them in the `get_api` function."
        )

    return TheiaAPI(username=username, password=password)


@validate_call(validate_return=True)
def set_credentials(
    username: str,
    password: str,
    directory: Optional[str] = None,
) -> None:
    """
    Sets user credentials in the specified directory by saving them to the .env.secret file
    using the dotenv package. If the credentials already exist and match the provided ones,
    the write operation is skipped.

    Parameters
    ----------
    username: str
        The username of the user's USGS account.
    password: str
        The password of the user's USGS account.
    directory: Optional[str]
        The directory where the .env.secret file will be saved. If not provided,
        the default directory is used based on the operating system.
    """

    if directory is None:
        if os.name == "posix":  # Linux and macOS
            xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
            if xdg_config_home:  # XDG_CONFIG_HOME is set
                config_dir = Path(xdg_config_home) / ".theia"
            else:
                if "Darwin" in os.uname().sysname:  # macOS
                    config_dir = (
                        Path.home() / "Library" / "Application Support" / ".theia"
                    )
                else:  # Linux
                    config_dir = Path.home() / ".config" / ".theia"
        elif os.name == "nt":  # Windows
            appdata = os.environ.get("APPDATA")
            if appdata:
                config_dir = Path(appdata) / ".theia"
            else:
                config_dir = Path.home() / ".theia"
        else:
            raise EnvironmentError("Unsupported operating system")

    else:
        config_dir = Path(directory)

    # Ensure the directory exists
    config_dir.mkdir(parents=True, exist_ok=True)

    # Define the path to the .env.secret file
    env_file_path = config_dir / ".env.secret"

    # Load existing credentials from the dotenv file
    existing_values = dotenv_values(dotenv_path=env_file_path)

    # Check if the provided credentials match the existing ones
    if (
        existing_values.get("USERNAME") == username
        and existing_values.get("PASSWORD") == password
    ):
        print(
            "Credentials already exist and match the provided values. No changes made."
        )
        return
    elif existing_values.get("USERNAME") or existing_values.get("PASSWORD"):
        print("Updating credentials with new values.")

    # Save the new credentials to the .env.secret file using dotenv
    set_key(env_file_path, "USERNAME", username)
    set_key(env_file_path, "PASSWORD", password)

    print(f"Credentials saved to {env_file_path}")
