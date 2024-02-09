import os
from typing import List
import time
from urllib.parse import urljoin

from pydantic import BaseModel, Json, PrivateAttr

import requests
import logging
from api.data_types import (
    AcquisitionFilter,
    CloudCoverFilter,
    Coordinate,
    Dataset,
    SceneFilter,
    SceneSearch,
    SearchParams,
    SpatialFilterMbr,
    User,
)
from api.util import check_exceptions
from api.errors import USGSRateLimitError

API_URL = "https://m2m.cr.usgs.gov/api/api/json/stable/"


class TheiaAPI(BaseModel):
    _logger: logging.Logger = PrivateAttr(default=logging.getLogger(__name__))
    _base_url: str = PrivateAttr(default=API_URL)
    _session: requests.sessions.Session = PrivateAttr(default_factory=requests.Session)
    _loggedIn: bool = PrivateAttr(default=False)
    _user: User = PrivateAttr(default=None)
    datasetDetails: List[Dataset] | None = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, username: str, password: str) -> None:
        super().__init__()
        self._user = User(username=username, password=password)
        self.setup_logging()
        self.login()
        if self._loggedIn:
            pass  # self._initDatasetDetails()

    def setup_logging(self) -> None:
        """
        Sets up logging for the TheiaAPI object.
        The log file is located in the directory where the code is run from.
        """
        # Configure the logger
        self._logger.setLevel(logging.DEBUG)

        # Create console handler and set level to INFO
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Create file handler and set level to DEBUG
        log_folder = "logs"
        os.makedirs(log_folder, exist_ok=True)
        log_file_path = os.path.join(log_folder, "theia_api.log")
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setLevel(logging.DEBUG)

        # Create formatter and add it to the handlers
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        # Add the handlers to the _logger
        self._logger.addHandler(console_handler)
        self._logger.addHandler(file_handler)

    def _initDatasetDetails(self) -> None:
        """
        Requests and stores the datasets that are available to the User
        accessing the USGS M2M API.
        """
        _datasetDetails = self._send_request_to_USGS("dataset-search").get("data")

        self.datasetDetails = [
            Dataset(
                collectionName=dataset["collectionName"],
                datasetAlias=dataset["datasetAlias"],
            )
            for dataset in _datasetDetails
        ]
        self.logout()

    def __del__(self) -> None:
        """
        Log the User out before destroying the TheiaAPI object.
        """
        self.logout()

    def login(self) -> None:
        """
        Method to login and retrieve the X-Auth-Token for future requests to the
        USGS M2M API. Uses the credentials passed when creating the API object.

        Notes
        -----
        Reference: https://m2m.cr.usgs.gov/api/docs/reference/#login
        """
        self._logger.info("Logging In")

        response = self._send_request_to_USGS("login", self._user.to_json())
        # Reference: https://m2m.cr.usgs.gov/api/docs/reference/#login-app-guest
        self._session.headers["X-Auth-Token"] = response.get("data")
        self._loggedIn = True

        self._logger.info("Logged In")

    def logout(self) -> None:
        """
        Method to logout of the USGS M2M API and discard the X-Auth-Token.

        Notes
        -----
        Reference: https://m2m.cr.usgs.gov/api/docs/reference/#logout
        Reference: https://m2m.cr.usgs.gov/api/docs/reference/#login-app-guest
        """
        self._logger.info("Logging Out")

        self._send_request_to_USGS("logout")
        self._session = requests.Session()
        self._loggedIn = False

        self._logger.info("Logged Out")

    def search_scenes(self, search_params: SearchParams) -> Json:
        """
        Searches the scenes as per the paramaters passed in search_params.

        Parameters
        ----------
        search_params: SearchParams
            A SearchParams class object containing parameters to be used in
            search.

        Returns
        -------
        response: requests.Response
            The response from the "scene-search" endpoint of the USGS M2M API.

        Notes
        -----
        Reference: https://m2m.cr.usgs.gov/api/docs/reference/#scene-search
        """
        scene_filter = self._generate_scene_filter(search_params)
        payload = SceneSearch(
            datasetName=search_params.dataset,
            sceneFilter=scene_filter,
            maxResults=search_params.max_results,
        )

        self._logger.info("Searching Scenes")
        self._logger.debug(f"Searching scenes with params {payload.to_pretty_json()}")

        response = self._send_request_to_USGS("scene-search", payload=payload.to_json())

        self._logger.info("Scene Search Successful")
        return response

    def _send_request_to_USGS(self, endpoint: str, payload: Json = "") -> Json:
        """
        Sends request to the USGS M2M API at the given endpoint with the given payload.

        Parameters
        ----------
        endpoint: str
            The endpoint of the USGS M2M API to send the request to.
        payload: Json
            The payload with the data to send to the USGS M2M API.
        """
        if not isinstance(payload, str):
            raise TypeError(
                "Expected 'payload' to be of type 'str',"
                f" got {type(payload)} instead"
            )

        response: requests.Response | None = None
        request_url = urljoin(self._base_url, endpoint)

        try:
            response = self._session.post(url=request_url, data=payload, timeout=600)
            check_exceptions(response)
        except USGSRateLimitError:
            time.sleep(3)
            response = self._session.post(url=request_url, data=payload)
            check_exceptions(response)

        return response.json()

    def _generate_scene_filter(self, params: SearchParams) -> SceneFilter:
        """
        Generates a scene filter.

        Parameters
        ----------
        params: SearchParams
            The parameters that are used to create the scene filter.

        Returns
        -------
        scene_filter: SceneFilter
            The generated scene filter.
        """
        if isinstance(params, SearchParams):
            filter_dict = {}

            if params.bbox is not None:
                filter_dict["spatialFilter"] = SpatialFilterMbr(
                    lowerLeft=params.bbox[0], upperRight=params.bbox[1]
                )
            elif params.longitude is not None and params.latitude is not None:
                filter_dict["spatialFilter"] = SpatialFilterMbr(
                    lowerLeft=Coordinate(
                        longitude=params.longitude, latitude=params.latitude
                    ),
                    upperRight=Coordinate(
                        longitude=params.longitude, latitude=params.latitude
                    ),
                )

            if params.start_date is not None and params.end_date is not None:
                filter_dict["acquisitionFilter"] = AcquisitionFilter(
                    start=params.start_date, end=params.end_date
                )

            if (
                params.max_cloud_cover is not None
                and params.min_cloud_cover is not None
            ):
                filter_dict["cloudCoverFilter"] = CloudCoverFilter(
                    min=params.min_cloud_cover, max=params.max_cloud_cover
                )
            elif params.max_cloud_cover is not None:
                filter_dict["cloudCoverFilter"] = CloudCoverFilter(
                    max=params.max_cloud_cover
                )
            elif params.min_cloud_cover is not None:
                filter_dict["cloudCoverFilter"] = CloudCoverFilter(
                    min=params.min_cloud_cover
                )
            else:
                filter_dict["cloudCoverFilter"] = CloudCoverFilter()

            if params.months is not None:
                filter_dict["seasonalFilter"] = params.months

            scene_filter = SceneFilter(**filter_dict)

            return scene_filter
        else:
            raise TypeError(
                "Expected 'params' to be of type 'SearchParams',"
                f" got {type(params)} instead"
            )
