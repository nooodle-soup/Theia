from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, validator
from typing import List, Union


class MetadataFilterType(Enum):
    VALUE = "value"
    AND = "and"
    OR = "or"
    BETWEEN = "between"


class SpatialFilterType(Enum):
    MBR = "mbr"
    GEOJSON = "geoJson"


class SceneIdentifier(Enum):
    ENTITYID = "entityId"
    DISPLAYID = "displayId"


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

    filterType: MetadataFilterType = Field(
        default=MetadataFilterType.VALUE, frozen=True, validate_default=True
    )
    filterId: str
    value: Union[str, float, int]
    operand: str = Field(default="=")


class SpatialFilter(BaseDataModel):
    """
    Abstract class for filtering spatially.

    Attributes
    ----------
    filterType: SpatialFilterType
        The type of spatial filter.
    """

    filterType: SpatialFilterType


class SpatialFilterMbr(SpatialFilter):
    """
    A class to apply spatial filter using mbr values on search.

    Attributes
    ----------
    filterType: SpatialFilterType, default = 'mbr'
        The type of spatial filter. Cannot be changed.
    lowerLeft: Coordinate
        Lower left coordinate for the mbr.
    upperRight: Coordinate
        Upper right coordinate for the mbr.

    Notes
    -----
    Reference: https://m2m.cr.usgs.gov/api/docs/datatypes/#spatialFilterMbr
    """

    filterType: SpatialFilterType = Field(
        default=SpatialFilterType.MBR, frozen=True, validate_default=True
    )
    lowerLeft: Coordinate
    upperRight: Coordinate


class SpatialFilterGeoJson(SpatialFilter):
    """
    A class to apply spatial filter using mbr values on search.

    Attributes
    ----------
    filterType: SpatialFilterType, default = 'geoJson'
        The type of spatial filter. Cannot be changed.
    geoJson: GeoJson
        GeoJson specifying the search region.

    Notes
    -----
    Reference: https://m2m.cr.usgs.gov/api/docs/datatypes/#spatialFilterGeoJson
    """

    filterType: SpatialFilterType = Field(
        SpatialFilterType.GEOJSON, frozen=True, validate_default=True
    )
    geoJson: GeoJson


class AcquisitionFilter(BaseDataModel):
    """
    A class to filter search using the acquisition dates of the satellite image.

    Attributes
    ----------
    start: str
        ISO8601 date string
    end: str
        ISO8601 date string

    Notes
    -----
    Reference: https://m2m.cr.usgs.gov/api/docs/datatypes/#acquisitionFilter
    """

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
    The scene filter to be applied during scene search.

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
    """
    Search parameters used to build the filters.

    Attributes
    ----------
    dataset: str
        The name of the dataset to search.
    longitude: Optional[float], default = None
        The longitude of the point of interest.
    latitude: Optional[float], default = None
        The latitude of the point of interest.
    bbox: Optional[List[Coordinate]], default = None
        The bounding box of the area of interest.
    max_cloud_cover: Optional[int], default = None
        The maximum acceptable cloud cover.
    min_cloud_cover: Optional[int], default = None
        The minimum acceptable cloud cover.
    start_date: Optional[str], default = None
        The start date for temporal filtering. Must be ISO8601 formatted.
    end_date: Optional[str], default = None
        The end date for temporal filtering. Must be ISO8601 formatted.
    months: Optional[List[int]], default = None
        The months for seasonal filtering. Accepted values are 1 through 12.
    max_results: Optional[int], default = 100
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


class DatasetFilters(BaseDataModel):
    """
    A class representing the json payload sent to "dataset-filters" endpoint
    to get the metadata filters of a dataset.

    Attributes
    ----------
    datasetName: str
        The name of the dataset.
    """

    datasetName: str


class SceneList(BaseDataModel):
    listId: str


class SceneListAdd(SceneList):
    datasetName: str
    idField: SceneIdentifier = Field(
        default=SceneIdentifier.ENTITYID, validate_default=True
    )
    entityId: str | None = None
    entityIds: List[str] | None = None
    timeToLive: str | None = None
    checkDownloadRestriction: bool | None = None

class SceneListRemove(SceneList):
    datasetName: str | None = None
    entityId: str | None = None
    entityIds: List[str] | None = None
