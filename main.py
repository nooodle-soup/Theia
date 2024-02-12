from dotenv import dotenv_values

from api import theia_api

config = {
    **dotenv_values(".env.shared"),  # load shared development variables
    **dotenv_values(".env.secret"),  # load sensitive variables
}


if config["USERNAME"] == "None":
    pass

if config["PASSWORD"] == "None":
    pass


def get_api():
    assert config["PASSWORD"] is not None
    assert config["USERNAME"] is not None
    api = theia_api.TheiaAPI(username=config["USERNAME"], password=config["PASSWORD"])
    return api
