from setuptools import setup
from setuptools.command.install import install
import configparser
import os


def create_config_file():
    # Determine the appropriate directory based on the operating system
    match os.name:
        case "posix":  # Linux or MacOS
            config_dir = os.path.join(
                os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
                "theia_api",
            )
        case "nt":  # Windows
            config_dir = os.path.join(os.environ["APPDATA"], "theia_api")
        case _:
            raise NotImplementedError("Unsupported operating system")

    # Create the directory if it doesn't exist
    os.makedirs(config_dir, exist_ok=True)

    # Define the configuration file path
    config_file_path = os.path.join(config_dir, "config.ini")

    # Write the configuration data to the file
    config = configparser.ConfigParser()
    config["DEFAULT"] = {"username": str(None), "password": str(None)}
    with open(config_file_path, "w") as configfile:
        config.write(configfile)


class PostInstallCommand(install):
    """Post-installation for installation mode."""

    def run(self):
        # Custom code to execute after installation
        create_config_file()

        # Call the parent class' run method
        install.run(self)


setup(
    name="theia",
    version="0.1",
    author="Vineet Agarwal",
    author_email="vineetagarwal2402@gmail.com",
    description="Description of your package",
    cmdclass={
        "install": PostInstallCommand,
    },
)
