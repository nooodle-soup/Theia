import os
import time
import requests
import threading
import logging
import pandas as pd
import datetime
import json
import re

from urllib.parse import urljoin
from typing import List, Tuple
from pydantic import BaseModel, ConfigDict, Json, PrivateAttr, validate_call
from requests import Response
from pandas import DataFrame

from theia.data_types import (
    AcquisitionFilter,
    CloudCoverFilter,
    Coordinate,
    Dataset,
    SceneFilter,
    SpatialFilterMbr,
)
from theia.endpoint_payload_types import (
    DatasetFiltersPayload,
    DataOwnerPayload,
    DatasetPayload,
    DownloadOptionsPayload,
    SceneListAddPayload,
    SearchParamsPayload,
    SceneSearchPayload,
)
from theia.util_types import (
    User,
)
from theia.errors import (
    USGSAuthenticationError,
    USGSError,
    USGSRateLimitError,
    USGSUnauthorizedError,
    USGSDatasetAuthError,
)

API_URL = "https://m2m.cr.usgs.gov/api/api/json/stable/"
MAX_THREADS = 5

_sema: threading.Semaphore = threading.Semaphore(value=MAX_THREADS)


class TheiaAPI(BaseModel):
    _logger: logging.Logger = PrivateAttr(default=logging.getLogger(__name__))
    _base_url: str = PrivateAttr(default=API_URL)
    _session: requests.sessions.Session = PrivateAttr(default_factory=requests.Session)
    _loggedIn: bool = PrivateAttr(default=False)
    _logout_timer: threading.Timer | None = PrivateAttr(default=None)
    _user: User = PrivateAttr(default=None)
    _threads: List[threading.Thread] = []
    datasetDetails: List[Dataset] | None = None
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, username: str, password: str) -> None:
        """
        Sets up `User` details and logging for the api object.

        Logs the user in and gets available dataset details.

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
        response = response.json()
        self._session.headers["X-Auth-Token"] = response.get("data")
        self._loggedIn = True
        self._logger.info("Logged in successfully")

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

    def data_owner(self, payload: DataOwnerPayload) -> Json:
        self._logger.info("Searching Data Owner")
        self._logger.debug(f"DataOwner Payload : {payload.to_pretty_json()}")
        response = self._send_request_to_USGS("data-owner", payload=payload.to_json())
        self._logger.info("Data Owner Found Successfully")

        return response.json()

    def dataset(self, payload: DatasetPayload) -> Json:
        self._logger.info("Searching Data Owner")
        self._logger.debug(f"DataOwner Payload : {payload.to_pretty_json()}")
        response = self._send_request_to_USGS("data-owner", payload=payload.to_json())
        self._logger.info("Data Owner Found Successfully")

        return response.json()

    def scene_search(self, payload: SceneSearchPayload) -> Json:
        """
        Searches the scenes as per the parameters passed in SceneSearch payload.

        Parameters
        ----------
        payload: SceneSearch
            A SceneSearch class object containing parameters to be used in
            search.

        Returns
        -------
        response: Json
            The response from the "scene-search" endpoint of the USGS M2M API.
            Returns an empty response if there is an error.

        Notes
        -----
        Reference: https://m2m.cr.usgs.gov/api/docs/reference/#scene-search
        """

        self._logger.info("Searching Scenes")
        self._logger.debug(f"Payload: {payload.to_pretty_json()}")
        response = self._send_request_to_USGS("scene-search", payload=payload.to_json())
        self._logger.info("Scene Search Successful")

        return response.json()

    def scene_list_add(self, payload: SceneListAddPayload) -> Json:
        """
        Adds scenes to a scene list.

        Parameters
        ----------
        payload: SceneListAddPayload
            A SceneListAddPayload class object containing field values to send to
            the scene-list-add endpoint.

        Returns
        -------
        response : requests.Response
            The response from the "scene-list-add" endpoint of the USGS M2M API.

        Notes
        -----
        Reference: https://m2m.cr.usgs.gov/api/docs/reference/#scene-list-add
        """
        self._logger.info("Adding scenes to the scene list...")
        self._logger.debug(f"Payload : {payload.to_pretty_json()}")
        response = self._send_request_to_USGS("scene-list-add", payload.to_json())
        self._logger.info("Scenes successfully added to the list...")

        return response.json()

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

        return response.json()

    def dataset_filters(self, payload: DatasetFiltersPayload) -> Json:
        """
        Searches for the available metadata fields for the dataset images.

        Parameters
        ----------
        payload: DatasetFilters
            The dataset filters to pass as the payload.

        Returns
        -------
        response: Json
            The response from the "dataset-filters" endpoint of the USGS M2M API.

        Notes
        -----
        Reference: https://m2m.cr.usgs.gov/api/docs/reference/#dataset-filters
        """
        self._logger.info("Searching Metadata Filter Fields")
        self._logger.debug(f"Payload : {payload.to_pretty_json()}")
        response = self._send_request_to_USGS("dataset-filters", payload.to_json())
        self._logger.info("Metadata Filter Fields Found")

        return response.json()

    def download_options(self, payload: DownloadOptionsPayload) -> Json:
        self._logger.info("Searching Download Options")
        self._logger.debug(f"Payload : {payload.to_pretty_json()}")
        response = self._send_request_to_USGS("download-options", payload.to_json())
        self._logger.info("Download Options Found")

        return response.json()

    def download_request(self, payload: DownloadRequestPayload) -> Json:
        self._logger.info("Searching Download Options")
        self._logger.debug(f"Payload : {payload.to_pretty_json()}")
        response = self._send_request_to_USGS("download-options", payload.to_json())
        self._logger.info("Download Options Found")

        return response.json()

    def permissions(self) -> Json:
        """
        Shows the permissions available for the `User` currently logged in
        to the USGS M2M API.

        Returns
        -------
        response: Json
            The response from the "permissions" endpoint of the M2M API.
        """
        self._logger.info("Fetching Permissions")
        response = self._send_request_to_USGS("permissions")
        self._logger.info("Permissions Fetched Successfully")

        return response.json()

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
                self._logout_timer.daemon = True
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

    def _send_request_to_USGS(
        self, endpoint: str, payload: Json = ""
    ) -> requests.Response:
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

        Raises
        ------
        TypeError
            If the payload is not a string.
        USGSRateLimitError
            If the request is rate-limited by the USGS M2M API.

        Notes
        -----
        This method includes error handling for various HTTP status codes and USGS-specific errors.
        """
        if not isinstance(payload, str):
            raise TypeError(
                "Expected 'payload' to be of type 'str',"
                f" got {type(payload)} instead"
            )

        response = Response()
        request_url = urljoin(self._base_url, endpoint)

        try:
            response = self._session.post(url=request_url, data=payload, timeout=600)
            self._check_exceptions(response)
        except USGSRateLimitError:
            time.sleep(3)
            response = self._session.post(url=request_url, data=payload)
            self._check_exceptions(response)

        return response

    def _check_exceptions(self, response: Response) -> None:
        """
        Utility method to check for exceptions in responses.

        Parameters
        ----------
        response: Response
            A requests.Response class object to check for exceptions.

        Raises
        ------
        USGSAuthenticationError
            If the response contains an authentication error.
        USGSUnauthorizedError
            If the response indicates the user is unauthorized.
        USGSRateLimitError
            If the response indicates the user has hit the rate limit.
        USGSDatasetAuthError
            If the response indicates a dataset authorization error.
        USGSError
            For all other errors not specifically handled.

        Notes
        -----
        This method inspects the response from the USGS M2M API and raises appropriate exceptions.
        """
        data = response.json()
        error = {"code": data.get("errorCode"), "msg": data.get("errorMessage")}
        msg = f"{error['code']}: {error['msg']}"

        match error["code"]:
            case "AUTH_INVALID" | "AUTH_KEY_INVALID":
                self._logger.error(msg)
                raise USGSAuthenticationError(msg)
            case "AUTH_UNAUTHORIZED":
                self._logger.error(msg)
                raise USGSUnauthorizedError(msg)
            case "RATE_LIMIT":
                self._logger.error(msg)
                raise USGSRateLimitError(msg)
            case "DATASET_AUTH":
                self._logger.error(msg)
                raise USGSDatasetAuthError(msg)
            case _:
                if error["code"] is not None:
                    self._logger.error(msg)
                    raise USGSError(msg)

    def _setup_logging(self) -> None:
        """
        Sets up logging for the `TheiaAPI` object.

        Notes
        -----
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
        self._logger.info("------------")

    @validate_call
    def generate_scene_filter(self, params: SearchParamsPayload) -> SceneFilter:
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

        Raises
        ------
        ValidationError
            If the `params` argument is not an instance of `SearchParams`.

        Notes
        -----
        This method converts the search parameters into a format suitable for the USGS M2M API.
        """
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

        if params.max_cloud_cover is not None and params.min_cloud_cover is not None:
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
            The dataframe containing all the data for each scene in the search
            results except for metadata and browse.

        Notes
        -----
        Each row of `metadata_df`, `browse_df`, and `results_df` is for one
        search result.
        """
        self._logger.info("Parsing Scene Search Results")
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
                result_browse_data[
                    f"{
                        key} Thumbnail Path"
                ] = item["thumbnailPath"]
            browse_data_list.append(result_browse_data)

        metadata_df = pd.DataFrame(metadata_list)
        browse_df = pd.DataFrame(browse_data_list)
        results_df = pd.DataFrame(results)
        results_df.drop(["browse", "metadata"], axis=1, inplace=True)

        self._logger.info("Scene Search Results Parsed Successfully")

        return (metadata_df, browse_df, results_df)

    def download_scene(
        self,
        dataset_name: str,
        path: str,
        scene_ids: List[str] | None = None,
        list_id: str | None = "",
        includeSecondaryFileGroups: bool | None = False,
    ) -> None:
        """
        Downloads the scenes specified by the scene_ids or scene_id.

        Parameters
        ----------
        dataset_name : str
            The name of the dataset.
        path : str
            The directory where downloaded files will be saved.
        scene_ids : List[str]
            A list of scene IDs to download.
        max_threads : int, default=5
            Maximum number of threads for concurrent downloads.
        list_id : str, default=""
            The ID of the scene list.

        Notes
        -----
        The method manages the download process using threading for efficiency.
        """

        payload = DownloadOptionsPayload(
            datasetName=dataset_name,
            listId=list_id,
            entityIds=scene_ids,
            includeSecondaryFileGroups=True if includeSecondaryFileGroups else False,
        )

        downloads = []

        try:
            self._logger.info("Retrieving Download Options")
            download_options = self.download_options(payload=payload)["data"]

            downloads = [
                {"entityId": product["entityId"], "productId": product["id"]}
                for product in download_options
                if product["available"]
            ]

        except USGSDatasetAuthError as e:
            self._logger.error(e)

        if downloads:
            requested_download_count = len(downloads)

            self._logger.info("Requesting Downloads")

            label = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            payload = {"downloads": downloads, "label": label}

            request_results = self._send_request_to_USGS(
                endpoint="download-request",
                payload=json.dumps(payload),
            ).json()
            request_results = request_results["data"]

            if request_results.get("preparingDownloads"):
                more_download_urls = self._send_request_to_USGS(
                    endpoint="download-retrieve",
                    payload=json.dumps({"label": label}),
                ).json()
                more_download_urls = more_download_urls["data"]

                self._manage_downloads(
                    more_download_urls,
                    request_results,
                    path,
                    requested_download_count,
                )
            else:
                for download in request_results["availableDownloads"]:
                    self._run_download(download["url"], path)

            self._logger.info("Downloading Files...")
            for thread in self._threads:
                thread.join()
            self._threads.clear()
            self._logger.info("All Downloads Complete...")
        else:
            self._logger.info("No available products for download.")

    def _manage_downloads(
        self,
        download_urls: dict,
        request_results: dict,
        path: str,
        requested_download_count: int,
    ) -> None:
        """
        Manages the download process, handling retries and threading.

        Parameters
        ----------
        download_urls : dict
            URLs for available downloads.
        request_results : dict
            Results from the download request.
        path : str
            The directory where downloaded files will be saved.
        sema : threading.Semaphore
            Semaphore to control the number of concurrent threads.
        requested_download_count : int
            The total number of downloads requested.

        Notes
        -----
        This method manages retries for downloads that are not immediately available.
        """
        download_ids = []

        for download in download_urls.get("available", []):
            if (
                str(download["downloadId"]) in request_results["newRecords"]
                or str(download["downloadId"]) in request_results["duplicateProducts"]
            ):
                download_ids.append(download["downloadId"])
                self._run_download(download["url"], path)

        for download in download_urls.get("requested", []):
            if (
                str(download["downloadId"]) in request_results["newRecords"]
                or str(download["downloadId"]) in request_results["duplicateProducts"]
            ):
                download_ids.append(download["downloadId"])
                self._run_download(download["url"], path)

        while len(download_ids) < (
            requested_download_count - len(request_results["failed"])
        ):
            preparingDownloads = (
                requested_download_count
                - len(download_ids)
                - len(request_results["failed"])
            )
            self._logger.info(
                f"{preparingDownloads} downloads are not available. Waiting for 30 seconds.",
            )
            time.sleep(30)
            self._logger.info("Trying to retrieve data...")

            label = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            payload = {"label": label}
            moreDownloadUrls = self._send_request_to_USGS("download-retrieve", payload)
            for download in moreDownloadUrls["available"]:
                if download["downloadId"] not in download_ids and (
                    str(download["downloadId"]) in request_results["newRecords"]
                    or str(download["downloadId"])
                    in request_results["duplicateProducts"]
                ):
                    download_ids.append(download["downloadId"])
                    self._run_download(download["url"], path)

    def _run_download(
        self,
        url: str,
        path: str,
    ) -> None:
        """
        Starts a new thread to handle a file download.

        Parameters
        ----------
        url : str
            The URL of the file to download.
        path : str
            The directory where the file will be saved.
        sema : threading.Semaphore
            Semaphore to control the number of concurrent threads.
        """
        thread = threading.Thread(target=self._download_file, args=(url, path))
        self._threads.append(thread)
        thread.start()

    def _download_file(self, url: str, path: str) -> None:
        """
        Downloads a file from the specified URL.

        Parameters
        ----------
        url : str
            The URL of the file to download.
        path : str
            The directory where the file will be saved.
        sema : threading.Semaphore
            Semaphore to control the number of concurrent threads.

        Notes
        -----
        This method handles the actual download of the file and saves it to disk.
        """
        _sema.acquire()
        try:
            response = requests.get(url, stream=True)
            disposition = response.headers.get("content-disposition")
            if disposition:
                filename = re.findall("filename=(.+)", disposition)[0].strip('"')
                self._logger.info(f"Downloading {filename}...")
                with open(os.path.join(path, filename), "wb") as f:
                    f.write(response.content)
                self._logger.info(f"Downloaded {filename}.")
        except Exception as e:
            self._logger.error(f"Failed to download from {url}. error: {e}")
        finally:
            _sema.release()
            self._logger.info("Sema released...")
