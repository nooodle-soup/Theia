from pydantic import Field, field_validator
from typing import List
from theia.util_types import BaseDataModel
from theia.data_types import Coordinate, SortCustomization, SceneFilter


class DataOwnerPayload(BaseDataModel):
    """
    Returns details about the data owner.

    Attributes
    ----------
    dataOwner: str
        Used to identify the data owner - this value comes from the dataset-search response.
    """

    dataOwner: str


class DatasetPayload:
    """
    Dataset to search for.

    Attributes
    ----------
    datasetId: str, optional
        The dataset identifier.
    datasetName: str, optional
        The system friendly dataset name.
    """

    datasetId: str | None = None
    datasetName: str | None = None


class SearchParamsPayload(BaseDataModel):
    """
    Search parameters used to build the filters.

    Attributes
    ----------
    dataset: str
        The name of the dataset to search.
    longitude: float, optional
        The longitude of the point of interest.
    latitude: float, optional
        The latitude of the point of interest.
    bbox: List[Coordinate], optional
        The bounding box of the area of interest.
    max_cloud_cover: int, optional
        The maximum acceptable cloud cover.
    min_cloud_cover: int, optional
        The minimum acceptable cloud cover.
    start_date: str, optional
        The start date for temporal filtering. Must be ISO8600 formatted.
    end_date: str, optional
        The end date for temporal filtering. Must be ISO8600 formatted.
    months: List[int], optional
        The months for seasonal filtering. Accepted values are 0 through 12.
    max_results: int, default = 99
        The maximum results to return for a search.
    """

    dataset: str
    longitude: float | None = Field(default=None)
    latitude: float | None = Field(default=None)
    bbox: List[Coordinate] | None = Field(default=None)
    max_cloud_cover: int | None = Field(default=None)
    min_cloud_cover: int | None = Field(default=None)
    start_date: str | None = Field(default=None)
    end_date: str | None = Field(default=None)
    months: List[int] | None = Field(default=None)
    max_results: int = Field(default=99)

    @field_validator('start_date', 'end_date', mode='before')
    @classmethod
    def check_start_end_dates(cls, v, info):
        # Access other fields
        other_field = 'end_date' if info.field_name == 'start_date' else 'start_date'
        other_value = info.data.get(other_field)
        
        # Check if only one of start_date or end_date is provided
        if (v is None and other_value is not None) or (v is not None and other_value is None):
            raise ValueError("Both start_date and end_date must be provided or neither.")
        
        return v

    @field_validator("longitude", "latitude", mode="before")
    @classmethod
    def check_longitude_latitude(cls, v, info):
        # Get the other field value
        other_field = "latitude" if info.field_name == "longitude" else "longitude"
        other_value = info.data.get(other_field)
        bbox = info.data.get("bbox")

        # Check if only one of longitude/latitude pair or bbox is provided
        if (v is not None or other_value is not None) and bbox is not None:
            raise ValueError("Cannot provide both longitude/latitude and bbox.")

        # Check if only one of longitude or latitude is provided
        if (v is None and other_value is not None) or (
            v is not None and other_value is None
        ):
            raise ValueError("Both longitude and latitude must be provided or neither.")

    @field_validator("bbox", mode="before")
    @classmethod
    def check_bbox(cls, v, info):
        longitude = info.data.get("longitude")
        latitude = info.data.get("latitude")

        # Check if bbox is provided with longitude/latitude
        if v is not None and (longitude is not None or latitude is not None):
            raise ValueError("Cannot provide both longitude/latitude and bbox.")

        return v


class SceneSearchPayload(BaseDataModel):
    """
    Contains the payload to be sent to the "scene-search" endpoint.

    Attributes
    ----------
    datasetName: str
        The dataset to be searched.
    maxResults: int, default=99
        The maximum results to be returned.
    startingNumber: int, optional
        The start number to search from.
    metadataType: {"full", "summary"}
        The metadata to return.
    sortField: str, optional
        The field to sort the results on.
    sortDirection: {"ASC", "DESC"}
        The direction in which the results are to be sorted.
    sortCustomization: SortCustomization, optional
        Specifies a custom sort.
    useCustomization: bool, optional
        Indicates whether to use customization.
    sceneFilter: SceneFilter, optional
        Specifies how to filter the data in the dataset.
    compareListName: str, optional
        Defines a scene-list listId to use to track scenes selected for comparison.
    bulkListName: str, optional
        Defined a scene-list listId to use to track scenes selected for bulk ordering.
    orderListName: str, optional
        Defined a scene-list listId to use to track scenes selected for on-demand ordering.
    excludeListName: str, optional
        Defined a scene-list listId to use to exclude scenes from the results.
    includeNullMetadataValues: bool, optional
        Optional parameter to include null metadata values.
    """

    datasetName: str
    maxResults: int | None = Field(default=99)
    startingNumber: int | None = Field(default=None)
    metadataType: str = Field(default="full", frozen=True)
    sortField: str | None = Field(default=None)
    sortDirection: str | None = Field(default=None)
    sortCustomization: SortCustomization | None = Field(default=None)
    useCustomization: bool | None = Field(default=None)
    sceneFilter: SceneFilter | None = Field(default=None)
    compareListName: str | None = Field(default=None)
    bulkListName: str | None = Field(default=None)
    orderListName: str | None = Field(default=None)
    excludeListName: str | None = Field(default=None)
    includeNullMetadataValues: bool | None = Field(default=None)


class DatasetFiltersPayload(BaseDataModel):
    """
    A class representing the json payload sent to "dataset-filters" endpoint
    to get the metadata filters of a dataset.

    Attributes
    ----------
    datasetName: str
        The name of the dataset.
    """

    datasetName: str


class DownloadOptionsPayload(BaseDataModel):
    """
    Data class for the download-options request in the USGS M1M API.

    Attributes
    ----------
    datasetName : str
        Dataset alias.
    entityIds : List[str], optional
        List of scene IDs.
    listId : str
        Used to identify the list of scenes to use.
    includeSecondaryFileGroups : bool, optional
        Optional parameter to return file group IDs with secondary products.
    """

    datasetName: str
    entityIds: List[str] | None = None
    listId: str | None = None
    includeSecondaryFileGroups: bool | None = True
