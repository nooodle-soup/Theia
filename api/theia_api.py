import json
from datetime import datetime
import sys
from typing import List, Type
import time
from urllib.parse import urljoin

from pydantic import BaseModel, PrivateAttr

import requests
from api.data_types import Coordinate, SearchParams, SpatialFilterMbr
from api.util import check_exceptions
from api.errors import USGSRateLimitError

API_URL = "https://m2m.cr.usgs.gov/api/api/json/stable/"


class TheiaAPI(BaseModel):
    _base_url: str = PrivateAttr(default=API_URL)
    _session: requests.sessions.Session = PrivateAttr(default_factory=requests.Session)

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, username, password):
        super().__init__()
        self.login(username, password)

    def __del__(self):
        self.logout()

    def login(self, username, password):
        params = {
            "username": username,
            "password": password
        }
        assert params is not None
        response = self._send_request_to_USGS("login", params)
        # Reference: https://m2m.cr.usgs.gov/api/docs/reference/#login-app-guest
        self._session.headers["X-Auth-Token"] = response

    def logout(self):
        # Reference: https://m2m.cr.usgs.gov/api/docs/reference/#login-app-guest
        # Reference: https://m2m.cr.usgs.gov/api/docs/reference/#logout
        self._send_request_to_USGS("logout")
        self._session = requests.Session()

    def _send_request_to_USGS(self, endpoint, params=None):
        response = None
        request_url = urljoin(self._base_url, endpoint)

        try:
            response = self._session.post(
                url=request_url,
                data=json.dumps(params)
            )
            check_exceptions(response)
        except USGSRateLimitError:
            time.sleep(3)
            response = self._session.post(
                url=request_url,
                data=json.dumps(params)
            )
            check_exceptions(response)

        assert response is not None
        return response.json().get("data")

    def search(self, params: Type[SearchParams]):
        if not isinstance(params, SearchParams):
            raise TypeError(
                "Expected 'params' to be of type 'SearchParams',"
                f" got {type(params)} instead"
            )

        spatialFilter = None
        if not params.bbox:
            assert params.latitude is not None
            assert params.longitude is not None
            spatialFilter = SpatialFilterMbr(
                lowerLeft=Coordinate(
                    longitude=params.longitude,
                    latitude=params.latitude
                ),
                upperRight=Coordinate(
                    longitude=params.longitude,
                    latitude=params.latitude
                ),
            )
        else:
            spatialFilter = SpatialFilterMbr(
                lowerLeft=params.bbox[0],
                upperRight=params.bbox[1]
            )


