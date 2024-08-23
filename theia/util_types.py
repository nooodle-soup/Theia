from pydantic import BaseModel, ConfigDict


class BaseDataModel(BaseModel):
    """
    Base class to be inherited by all data classes.
    Contains methods to make conversion to json convenient.
    """

    model_config = ConfigDict(use_enum_values=True)

    def to_json(self):
        return self.model_dump_json(exclude_none=True)

    def to_pretty_json(self):
        return self.model_dump_json(exclude_none=True, indent=2)


class User(BaseDataModel):
    """
    A class to store user credentials.

    Attributes
    ----------
    username: str
        User's USGS username.
    password: str
        User's USGS password.
    """

    username: str
    password: str
