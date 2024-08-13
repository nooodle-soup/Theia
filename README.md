### TheiaAPI - Python Wrapper for USGS M2M API

TheiaAPI is a Python wrapper for the USGS Machine-to-Machine (M2M) API, providing functionality to search, retrieve metadata, and download satellite imagery datasets. This library is designed to streamline interaction with the USGS API, offering robust error handling, logging, and threading capabilities for efficient data retrieval.

## Features
*Login/Logout*: Authenticate with the USGS M2M API using your credentials.
*Scene and Dataset Search*: Search for scenes and datasets based on various filters.
*Metadata Retrieval*: Fetch available metadata fields for specific datasets.
*Scene Download*: Download satellite imagery scenes with support for concurrent downloads using threading.
*Permissions Check*: View the permissions available for the authenticated user.
*Logging*: Comprehensive logging to track API interactions, errors, and download progress.

## Installation
To install TheiaAPI, clone the repository and ensure you have the necessary dependencies installed:

```bash
git clone https://github.com/yourusername/theia-api.git
cd theia-api
pip install -r requirements.txt
```

## Usage
# Initialize the API
```python
from theia_api import TheiaAPI

api = TheiaAPI(username=`your_username`, password=`your_password`)
```

# Search for Scenes
```python
search_params = SearchParams(
    dataset=`LANDSAT_8`,
    bbox=[Coordinate(latitude=40.7128, longitude=-74.0060), Coordinate(latitude=40.7306, longitude=-73.9352)],
    start_date=`2020-01-01`,
    end_date=`2020-12-31`,
    max_results=10
)
response = api.scene_search(search_params)
```

# Download Scenes
```python
api.download_scene(
    dataset_name=`LANDSAT_8`,
    path=`./downloads`,
    scene_ids=[`LC08_L1TP_011029_20200414_20200414_01_RT`]
)
```

# View Permissions
```python
permissions = api.permissions()
print(permissions)
```

# Logging Out
```python
api.logout()
```

## Notes
The download functionality supports multiple concurrent downloads using threading, 
which can be customized with the MAX_THREADS constant.

TheiaAPI includes built-in error handling for various HTTP status codes and USGS-specific errors.
Ensure that the logout timer is managed properly to avoid unnecessary API calls.

## License
This project is licensed under the MIT License.


