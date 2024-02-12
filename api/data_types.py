from enum import Enum
from pydantic import BaseModel, Field, validator
from typing import List, Union


class MetadataFilterType(Enum):
    VALUE = "value"
    AND = "and"
    OR = "or"
    BETWEEN = "between"


class BaseDataModel(BaseModel):
    """
    Base class to be inherited by all data classes.
    Contains methods to make conversion to json convenient.
    """

    def to_json(self):
        return self.model_dump_json(exclude_none=True)

    def to_pretty_json(self):
        return self.model_dump_json(exclude_none=True, indent=2)


class Dataset(BaseModel):
    """
    A class to store USGS Dataset details.

    Attributes
    ----------
    collectionName: str
        The dataset's collection name.
    datasetAlias: str
        The dataset's alias.
    """

    collectionName: str
    datasetAlias: str


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


class Coordinate(BaseDataModel):
    """
    A class to store coordinate data.

    Attributes
    ----------
    longitude: float
        The longitude of the coordinate.
    latitude: float
        The latitude of the coordinate.

    Notes
    -----
    Reference: https://m2m.cr.usgs.gov/api/docs/datatypes/#coordinate
    """

    longitude: float
    latitude: float


class GeoJson(BaseDataModel):
    """
    A class that stores GeoJson data.

    Attributes
    ----------
    type: str
        Geometry types supported by GeoJson.
    coordinate: List[Coordinate]
        Coordinate array.

    Notes
    -----
    Reference: https://m2m.cr.usgs.gov/api/docs/datatypes/#geoJson
    """

    type: str
    coordinates: List[Coordinate]

    @classmethod
    def transform(cls, shape):
        type = shape["type"]
        coordinates = shape["coordinates"]

        if type == "MultiPolygon":
            return cls(
                type=type,
                coordinates=[
                    Coordinate(**point)
                    for polygon in coordinates[0]
                    for point in polygon
                ],
            )
        elif type == "Polygon":
            return cls(
                type=type, coordinates=[Coordinate(**point) for point in coordinates[0]]
            )
        elif type == "LineString":
            return cls(
                type=type, coordinates=[Coordinate(**point) for point in coordinates]
            )
        elif type == "Point":
            return cls(type=type, coordinates=[Coordinate(**coordinates)])
        else:
            raise ValueError(f"Geometry type `{type}` not supported.")


class MetadataFilter(BaseDataModel):
    """
    Abstract class for filtering by metadata.

    Attributes
    ----------
    filterType: MetadataFilterType
        The type of metadata filter.
    """

    filterType: MetadataFilterType


class MetadataValue(MetadataFilter):
    """
    A class to apply metadata filter using metadata values on search.

    Attributes
    ----------
    filterType: MetadataFilterType, default = 'value'
        The type of metadata filter. Cannot be changed.
    filterId: str
        Unique Identifier for the dataset criteria field.
    value: Union[str, float, int]
        The value of use.
    operand: {'=', 'like'}
        The operand to search with.

    Notes
    -----
    Reference: https://m2m.cr.usgs.gov/api/docs/datatypes/#metadataValue
    """

    filterType: MetadataFilterType = Field(default="value", frozen=True)
    filterId: str
    value: Union[str, float, int]
    operand: str = Field(default="=")


class SpatialFilterMbr(BaseDataModel):
    # Reference: https://m2m.cr.usgs.gov/api/docs/datatypes/#spatialFilterMbr
    filterType: str = Field(default="mbr", frozen=True)
    lowerLeft: Coordinate
    upperRight: Coordinate


class SpatialFilterGeoJson(BaseDataModel):
    # Reference: https://m2m.cr.usgs.gov/api/docs/datatypes/#spatialFilterGeoJson
    filterType: str = Field("geoJson", frozen=True)
    geoJson: GeoJson


class AcquisitionFilter(BaseDataModel):
    # Reference: https://m2m.cr.usgs.gov/api/docs/datatypes/#acquisitionFilter
    start: str
    end: str


class CloudCoverFilter(BaseDataModel):
    """
    Used to limit results by cloud cover (for supported datasets).

    Attributes
    ----------
    min: int, default = 0
        The minimum acceptable cloud cover.
    max: int, default = 30
        The maximum acceptable cloud cover.

    Notes
    -----
    Reference: https://m2m.cr.usgs.gov/api/docs/datatypes/#cloudCoverFilter
    """

    min: int = 0
    max: int = 30
    includeUnknown: bool = False


class DateRange(BaseDataModel):
    """
    Stores the start and end dates for the dateRange to apply a temporal filter
    on the search criteria.

    Attributes
    ----------
    startDate: str
        ISO8601 date string
    endDate: str
        ISO8601 date string

    Notes
    -----
    Reference: https://m2m.cr.usgs.gov/api/docs/datatypes/#dateRange
    """

    startDate: str
    endDate: str


class SceneFilter(BaseDataModel):
    """

    Attributes
    ----------
    acquisitionFilter: AcquisitionFilter, optional
        The acquisition filter to apply on the data.
    cloudCoverFilter: CloudCoverFilter, optional
        The cloud cover filter to apply on the data.
    datasetName: string, optional
        The dataset name to search the scene in.
    ingestFilter: IngestFilter, optional
        The ingest filter to apply on the data.
    metadataFilter: Union[MetadataAnd, MetadataOr, MetadataBetween, MetadataValue], optional
        The metadataFilter to apply on the data.
    seasonalFilter: list of int, optional
        The months to filter the data on. Acceptable values from 1 through 12.
    spatialFilter: Union[SpatialFilterMbr, SpatialFilterGeoJson], optional
        The spatial filter to apply on the data.

    Notes
    -----
    Reference: https://m2m.cr.usgs.gov/api/docs/datatypes/#sceneFilter
    """

    acquisitionFilter: AcquisitionFilter | None = None
    cloudCoverFilter: CloudCoverFilter | None = None
    datasetName: str | None = None
    metadataFilter: MetadataValue | None = None
    seasonalFilter: List[int] | None = None
    spatialFilter: SpatialFilterMbr | SpatialFilterGeoJson | None = None


class SortCustomization(BaseDataModel):
    pass


class SearchParams(BaseDataModel):
    dataset: str
    longitude: float | None = Field(default=None)
    latitude: float | None = Field(default=None)
    bbox: List[Coordinate] | None = Field(default=None)
    max_cloud_cover: int | None = Field(default=None)
    min_cloud_cover: int | None = Field(default=None)
    start_date: str | None = Field(default=None)
    end_date: str | None = Field(default=None)
    months: List[int] | None = Field(default=None)
    max_results: int = Field(default=100)

    @validator("start_date", pre=True, always=True)
    def check_start_date(cls, v, values):
        if "end_date" in values and values["end_date"] is not None and v is None:
            raise ValueError("Start date must be provided when End date is provided")
        return v

    @validator("end_date", pre=True, always=True)
    def check_end_date(cls, v, values):
        if "start_date" in values and values["start_date"] is not None and v is None:
            raise ValueError("End date must be provided when Start date is provided")
        return v

    @validator("longitude", pre=True, always=True)
    def check_longitude(cls, v, values):
        if "latitude" in values and values["latitude"] is not None and v is None:
            raise ValueError("Longitude must be provided when latitude is provided")
        return v

    @validator("latitude", pre=True, always=True)
    def check_latitude(cls, v, values):
        if "longitude" in values and values["longitude"] is not None and v is None:
            raise ValueError("Latitude must be provided when longitude is provided")
        return v

    @validator("bbox", pre=True, always=True)
    def check_bbox(cls, v, values):
        if (
            "longitude" in values
            and "latitude" in values
            and values["longitude"] is not None
            and values["latitude"] is not None
        ):
            if v is not None:
                raise ValueError(
                    "Either provide longitude and latitude or bbox, not both"
                )
        return v


class SceneSearch(BaseDataModel):
    """
    Contains the payload to be sent to the "scene-search" endpoint.

    Attributes
    ----------
    datasetName: str
        The dataset to be searched.
    maxResults: int, default=100
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
    maxResults: int | None = Field(default=100)
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
