import os
import time
import requests
import threading
import logging
import pandas as pd

from urllib.parse import urljoin
from typing import List, Tuple
from pydantic import BaseModel, ConfigDict, Json, PrivateAttr
from requests import Response
from pandas import DataFrame

from data_types import (
    AcquisitionFilter,
    CloudCoverFilter,
    Coordinate,
    Dataset,
    DatasetFilters,
    SceneFilter,
    SceneSearch,
    SearchParams,
    SpatialFilterMbr,
    User,
)
from errors import (
    USGSAuthenticationError,
    USGSError,
    USGSRateLimitError,
    USGSUnauthorizedError,
)

API_URL = "https://m2m.cr.usgs.gov/api/api/json/stable/"


class TheiaAPI(BaseModel):
    _logger: logging.Logger = PrivateAttr(default=logging.getLogger(__name__))
    _base_url: str = PrivateAttr(default=API_URL)
    _session: requests.sessions.Session = PrivateAttr(default_factory=requests.Session)
    _loggedIn: bool = PrivateAttr(default=False)
    _logout_timer: threading.Timer | None = PrivateAttr(default=None)
    _user: User = PrivateAttr(default=None)
    datasetDetails: List[Dataset] | None = None
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, username: str, password: str) -> None:
        """
        Sets up `User` details and logging for the api object.
        Logs the user in and gets availabel dataset details.

        Parameters
        ----------
        username: str
            The user's USGS username.
        password: str
            The user's USGS password.
        """
        super().__init__()
        self._user = User(username=username, password=password)
        self._setup_logging()
        self._logout_timer_manager(switch="start")
        self.login()
        if self._loggedIn:
            pass  # self._initDatasetDetails()

    def __del__(self) -> None:
        """
        Logs the User out and stops the login timer before destroying the
        `TheiaAPI` object.
        """
        self._logout_timer_manager(switch="stop")
        self.logout()

    def login(self) -> None:
        """
        Method to login and retrieve the X-Auth-Token for future requests to the
        USGS M2M API. Uses the credentials passed when creating the API object.

        Notes
        -----
        Reference: https://m2m.cr.usgs.gov/api/docs/reference/#login
        Reference: https://m2m.cr.usgs.gov/api/docs/reference/#login-app-guest
        """
        if self._loggedIn:
            self.logout()

        self._logger.info("Logging In")

        response = self._send_request_to_USGS("login", self._user.to_json())
        self._session.headers["X-Auth-Token"] = response.get("data")
        self._loggedIn = True

        self._logger.info("Logged In")

    def logout(self) -> None:
        """
        Method to logout of the USGS M2M API and discard the X-Auth-Token.

        Notes
        -----
        Logging out is not necessary but is strongly recommended after two
        hours, as that is the Auth Token duration.
        Reference: https://m2m.cr.usgs.gov/api/docs/reference/#logout
        """
        self._logger.info("Logging Out")

        self._send_request_to_USGS("logout")
        self._session = requests.Session()
        self._loggedIn = False

        self._logger.info("Logged Out")

    def scene_search(self, search_params: SearchParams) -> Json:
        """
        Searches the scenes as per the paramaters passed in `search_params`.

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

    def dataset_search(self) -> Json:
        """
        Searches datasets available to the user.

        Returns
        -------
        response: Json
            The response from the "dataset-search" endpoint of the USGS M2M API.

        Notes
        -----
        Reference: https://m2m.cr.usgs.gov/api/docs/reference/#dataset-search
        """
        self._logger.info("Searching Datasets")

        response = self._send_request_to_USGS("dataset-search")

        self._logger.info("Dataset Details Retrieved")
        return response

    def dataset_filters(self, dataset: str) -> Json:
        """
        Searches for the available metadata fields for the dataset images.

        Parameters
        ----------
        dataset: str
            The dataset to get the metadata fields for.

        Returns
        -------
        response: Json
            The response from the "dataset-filters" endpoint of the USGS M2M API.

        Notes
        -----
        Reference: https://m2m.cr.usgs.gov/api/docs/reference/#dataset-filters
        """
        self._logger.info("Searching Metadata Filter Fields")

        payload = DatasetFilters(datasetName=dataset)

        response = self._send_request_to_USGS("dataset-filters", payload.to_json())

        self._logger.info(f"Metadata Filter Fields Found For {dataset}")
        return response

    def parse_scene_search_results(
        self, response: Json
    ) -> Tuple[DataFrame, DataFrame, DataFrame]:
        """
        Parses the response from the `scene_search` method.

        Parameters
        ----------
        response: Json
            The response from `scene_search`.

        Returns
        -------
        metadata_df: DataFrame
            The dataframe containing the metadata for each scene in the search
            results.
        browse_df: DataFrame
            The dataframe containing the thumbnails for each scene in the search
            results.
        results_df: DataFrame
            The dataframe containing all the data for each scene it the search
            results except for metadata and browse.

        Notes
        -----
        Each row of `metadata_df`, `browse_df` and `results_df` is for one
        search result.
        """
        results = response.get("data").get("results")
        metadata_list = []
        browse_data_list = []

        for result in results:
            result_metadata = {}
            for item in result["metadata"]:
                result_metadata[item["fieldName"]] = item["value"]
            metadata_list.append(result_metadata)

            result_browse_data = {}
            for item in result["browse"]:
                key = item["browseName"]
                result_browse_data[f"{key} Browse Path"] = item["browsePath"]
                result_browse_data[f"{key} Thumbnail Path"] = item["thumbnailPath"]
            browse_data_list.append(result_browse_data)

        metadata_df = pd.DataFrame(metadata_list)
        browse_df = pd.DataFrame(browse_data_list)
        results_df = pd.DataFrame(results)
        results_df.drop(["browse", "metadata"], axis=1, inplace=True)

        return (metadata_df, browse_df, results_df)

    def permissions(self) -> Json:
        """
        Shows the permissions available for the `User` currently logged in
        to the USGS M2M API.

        Returns
        -------
        response: Json
            The response from the "permissions" endpoint of the M2M API.
        """
        response = self._send_request_to_USGS("permissions")

        return response

    def scene_list_add(self, payload):
        pass

    def _initDatasetDetails(self) -> None:
        """
        Requests and stores the datasets that are available to the user
        accessing the USGS M2M API.
        """
        _datasetDetails = self.dataset_search().get("data")

        self.datasetDetails = [
            Dataset(
                collectionName=dataset["collectionName"],
                datasetAlias=dataset["datasetAlias"],
            )
            for dataset in _datasetDetails
        ]

    def _logout_timer_manager(self, switch: str = "start") -> None:
        """
        Handles the logout timer initialization and cancellation.

        Parameters
        ----------
        switch: {"start", "stop"}
            Tells the manager what to do with the timer.
        """
        match switch:
            case "start":
                self._logout_timer = threading.Timer(2 * 60 * 60, self._reset_login)
                self._logout_timer.start()
            case "stop":
                assert self._logout_timer is not None
                self._logout_timer.cancel()

    def _reset_login(self) -> None:
        """
        Deals with logging out, resetting the timer, and logging in again after
        the timer expires.
        """
        self.logout()
        self._logout_timer_manager(switch="start")
        self.login()

    def _send_request_to_USGS(self, endpoint: str, payload: Json = "") -> Json:
        """
        Sends request to the USGS M2M API at the given endpoint with the given payload.

        Parameters
        ----------
        endpoint: str
            The endpoint of the USGS M2M API to send the request to.
        payload: Json
            The payload with the data to send to the USGS M2M API.

        Returns
        -------
        response: Json
            The response from the request made to the `endpoint` converted to json.
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
            self._check_exceptions(response)
        except USGSRateLimitError:
            time.sleep(3)
            response = self._session.post(url=request_url, data=payload)
            self._check_exceptions(response)

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

    def _check_exceptions(self, response: Response) -> None:
        """
        Utility method to check for exceptions in responses.

        Parameters
        ----------
        response: Response
            A requests.Response class object to check for exceptions.

        Raises
        ------
        #####################TODO##############################
        """
        data = response.json()
        error = {"code": data.get("errorCode"), "msg": data.get("errorMessage")}
        msg = f"{error['code']}: {error['msg']}"

        match error["code"]:
            case "AUTH_INVALID" | "AUTH_KEY_INVALID":
                raise USGSAuthenticationError(msg)
            case "AUTH_UNAUTHORIZED":
                raise USGSUnauthorizedError(msg)
            case "RATE_LIMIT":
                raise USGSRateLimitError(msg)
            case _:
                if error["code"] is not None:
                    raise USGSError(msg)

    def _setup_logging(self) -> None:
        """
        Sets up logging for the `TheiaAPI` object.
        The log file is located in the directory where the code is run from.
        """
        self._logger.setLevel(logging.DEBUG)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        log_folder = "logs"
        os.makedirs(log_folder, exist_ok=True)
        log_file_path = os.path.join(log_folder, "theia_api.log")
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        self._logger.addHandler(console_handler)
        self._logger.addHandler(file_handler)
