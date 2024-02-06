from pydantic import BaseModel, Field, validator
from typing import List, Union


class Dataset(BaseModel):
    collectionName: str
    datasetAlias: str


class BaseDataModel(BaseModel):
    def to_json(self):
        return self.model_dump_json(exclude_unset=True)


class Coordinate(BaseDataModel):
    # Reference: https://m2m.cr.usgs.gov/api/docs/datatypes/#coordinate
    longitude: float
    latitude: float


class GeoJson(BaseDataModel):
    # Reference: https://m2m.cr.usgs.gov/api/docs/datatypes/#geoJson
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


class MetadataValue(BaseDataModel):
    # Reference: https://m2m.cr.usgs.gov/api/docs/datatypes/#metadataValue
    filterType: str = Field(default="value", frozen=True)
    filterId: str
    value: Union[str, float, int]
    operand: str

    @validator("operand", pre=True, always=True)
    def set_operand(cls, _, values):
        if isinstance(values["value"], str):
            return "like"
        else:
            return "="


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
    # Reference: https://m2m.cr.usgs.gov/api/docs/datatypes/#cloudCoverFilter
    min: int = 0
    max: int = 100
    includeUnknown: bool = False


class DateRange(BaseDataModel):
    # Reference: https://m2m.cr.usgs.gov/api/docs/datatypes/#dateRange
    startDate: str
    endDate: str


class SceneFilter(BaseDataModel):
    # Reference: https://m2m.cr.usgs.gov/api/docs/datatypes/#sceneFilter
    acquisitionFilter: AcquisitionFilter | None = None
    cloudCoverFilter: CloudCoverFilter | None = None
    datasetName: str | None = None
    metadataFilter: MetadataValue | None = None
    seasonalFilter: List[int] | None = None
    spatialFilter: SpatialFilterMbr | SpatialFilterGeoJson | None = None


class SearchParams(BaseModel):
    dataset: Dataset = Field(default=None)
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
