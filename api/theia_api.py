import json
import string
import random
from datetime import datetime
from dateutil import parser
import time
from urllib.parse import urljoin

import requests

from util import check_exceptions
from errors import USGSRateLimitError

API_URL = "https://m2m.cr.usgs.gov/api/api/json/stable/"


class TheiaAPI(object):

    def __init__(self, username, password):
        self._base_url = API_URL
        self._session = requests.Session()
        self._login(username, password)

    def _login(self, username, password):
        params = {
            "username": username,
            "password": password
        }
        assert params is not None
        response = self._send_request_to_USGS("login", params)
        # Reference: https://m2m.cr.usgs.gov/api/docs/reference/#login-app-guest
        self._session.headers["X-Auth-Token"] = response

    def _logout(self):
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
