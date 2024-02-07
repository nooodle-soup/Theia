import json
from typing import List, Type
import time
from urllib.parse import urljoin

from pydantic import BaseModel, PrivateAttr

import requests
from api.data_types import (
    AcquisitionFilter,
    CloudCoverFilter,
    Coordinate,
    Dataset,
    SceneFilter,
    SearchParams,
    SpatialFilterMbr,
    User,
)
from api.util import check_exceptions
from api.errors import USGSRateLimitError

API_URL = "https://m2m.cr.usgs.gov/api/api/json/stable/"


class TheiaAPI(BaseModel):
    _base_url: str = PrivateAttr(default=API_URL)
    _session: requests.sessions.Session = PrivateAttr(default_factory=requests.Session)
    _loggedIn: bool = PrivateAttr(default=False)
    _user: User = PrivateAttr(default=None)
    datasetDetails: List[Dataset] | None = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, username, password):
        super().__init__()
        self._user = User(username=username, password=password)
        self.login()
        if self._loggedIn:
            pass  # self._initDatasetDetails()

    def _initDatasetDetails(self):
        _datasetDetails = (
            self._send_request_to_USGS("dataset-search").json().get("data")
        )

        self.datasetDetails = [
            Dataset(
                collectionName=dataset["collectionName"],
                datasetAlias=dataset["datasetAlias"],
            )
            for dataset in _datasetDetails
        ]
        self.logout()

    def __del__(self):
        self.logout()

    def login(self):
        print("LOGGING IN")
        response = self._send_request_to_USGS("login", self._user.to_json())
        # Reference: https://m2m.cr.usgs.gov/api/docs/reference/#login-app-guest
        self._session.headers["X-Auth-Token"] = response.json().get("data")
        self._loggedIn = True
        print("LOGGED IN")

    def logout(self):
        # Reference: https://m2m.cr.usgs.gov/api/docs/reference/#login-app-guest
        # Reference: https://m2m.cr.usgs.gov/api/docs/reference/#logout
        print("LOGGING OUT")
        self._send_request_to_USGS("logout")
        self._session = requests.Session()
        self._loggedIn = False
        print("LOGGED OUT")

    def search(self, search_params: Type[SearchParams]):
        scene_filter = self._generate_search_filter(search_params)
        payload = json.dumps(
            {
                "datasetName": search_params.dataset,
                "sceneFilter": scene_filter,
                "maxResults": search_params.max_results,
                "metadataType": "full",
            }
        )
        response = self._send_request_to_USGS("scene-search", params=payload)
        return response

    def _send_request_to_USGS(self, endpoint: str, params: str = ""):
        if not isinstance(params, str):
            raise TypeError(
                "Expected 'params' to be of type 'str'," f" got {type(params)} instead"
            )
        response = None
        request_url = urljoin(self._base_url, endpoint)

        try:
            response = self._session.post(url=request_url, data=params, timeout=600)
            check_exceptions(response)
        except USGSRateLimitError:
            time.sleep(3)
            response = self._session.post(url=request_url, data=params)
            check_exceptions(response)

        return response

    def _generate_search_filter(self, params: Type[SearchParams]):
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

            sceneFilter = SceneFilter(**filter_dict)

            return sceneFilter.to_json()
        else:
            raise TypeError(
                "Expected 'params' to be of type 'SearchParams',"
                f" got {type(params)} instead"
            )
