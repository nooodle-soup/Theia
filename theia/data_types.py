from enum import Enum
from pydantic import Field, field_validator, validator, root_validator
from typing import List, Union
from theia.util_types import BaseDataModel


class SortOrderType(Enum):
    ASC = "ASC"
    DESC = "DESC"


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


class Dataset(BaseDataModel):
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


# ========================
# || General Data Types ||
# ========================


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


# =========================
# || Download Data Types ||
# =========================


class Download(BaseDataModel):
    """
    Data class representing a Download data type.

    Attributes
    ----------
    entityId : str
        Entity Identifier.
    productId : str
        Product Identifier.
    dataUse : str, optional
        The type of use of this data.
    label : str, optional
        The label name used when requesting the download.
    """

    entityId: str
    productId: str
    dataUse: str | None = None
    label: str | None = None


class FilegroupDownload(BaseDataModel):
    """
    Data class representing a FilegroupDownload data type.

    Attributes
    ----------
    datasetName: str
        Dataset name.
    fileGroups: List[str]
        Internal codes used to represent the file groups.
    listId: str, optional
        The name of scene list to request from.
    dataUse: str, optional
        The type of use of this data.
    label: str, optional
        The label name used when requesting the download.
    """

    datasetName: str
    fileGroups: List[str]
    listId: str | None = None
    dataUse: str | None = None
    label: str | None = None


class FilepathDownload(BaseDataModel):
    """
    Data class representing a FilepathDownload data type.

    Attributes
    ----------
    datasetName: str
        Dataset name.
    productCode: str
        Internal code used to represent this product during ordering.
    dataPath: str, optional
        The data location to stream the download from.
    dataUse: str, optional
        The type of use of this data.
    label: str, optional
        The label name used when requesting the download.
    """

    datasetName: str
    productCode: str
    dataPath: str | None = None
    dataUse: str | None = None
    label: str | None = None


class SortCustomization(BaseDataModel):
    """
    Data class representing a SortCustomization data type.

    Attributes
    ----------
    field_name: str
        Used to identify which field you want to sort by.
    direction: SortOrderType
        Used to determine which directions to sort (ASC, DESC).
    """

    field_name: str
    direction: SortOrderType
