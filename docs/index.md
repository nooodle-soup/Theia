# Theia

Welcome to Theia!
Theia is a Python package that provides a comprehensive interface for interacting 
with the USGS M2M API. It simplifies the process of searching, 
filtering, and downloading satellite imagery, making it ideal for anyone looking to
interact with the M2M API.

* [Overview](#overview)
* [Key Features](#key-features)
* [Getting Started](#getting-started)
    * [Installation](#installation)
    * [Basic Configuration](#basic-configuration)


## Overview

The Theia package is designed to streamline interactions with the USGS M2M API, 
offering robust functionality for managing user authentication, querying datasets, 
and retrieving data efficiently. Whether you're working on scientific research,
environmental monitoring, or any project requiring geospatial data, Theia provides 
a reliable and easy-to-use solution.

## Key Features

* #### Easy Authentication Management
    Theia handles user authentication seamlessly, including login, logout, and token 
    management.

* #### Comprehensive API Interaction
    Supports a wide range of operations, such as dataset searching, scene searching, 
    filtering options, and download management for both internal and external users.

* #### Data Filtering
    Allows for precise searches with customizable parameters like spatial filters 
    (bounding box, GeoJSON), cloud cover, acquisition dates, and more.

* #### Efficient Download Handling
    Multi-threaded download support ensures faster and more reliable data retrieval.

* #### Error Handling and Logging
    Built-in logging and custom error classes provide robust error management and 
    debugging support.


## Getting Started

### Installation

```bash title="Install using pip"
pip install theia
```

```bash title="Install using conda"
conda install conda-forge::theia
```

### Basic Configuration

To start using Theia, you'll need to set up your USGS M2M API credentials. You can 
do this using environment variables or by directly passing them when creating the 
`Theia` object.


Note that you will require access to the M2M API to be able to use Theia. You can 
get access [here](https://ers.cr.usgs.gov/profile/access "EROS Registration System - Access Control").

```py
from theia import Theia

api = Theia(username="YOUR_USERNAME", password="YOUR_PASSWORD")
```

You can now use the `api` object to interact with the server.

Passing your username and password every time to create an object can become a 
bit tedious, so I would suggest using a dotenv file to securely save them and 
use it as needed.

### Example Usage

Here's a quick example of how to perform a scene search with Theia:

```py
from theia import Theia, SearchParamsPayload

# Initialize the API
api = Theia(username="YOUR_USERNAME", password="YOUR_PASSWORD")

# Define search parameters
params = SearchParamsPayload(
    dataset='LANDSAT_8_C1',
    longitude=-100.0,
    latitude=40.0,
    max_cloud_cover=10,
    start_date='2023-01-01',
    end_date='2023-06-30'
)

# Perform a scene search
response = api.scene_search(params)
print(response)
```

This code snippet logs you into the USGS M2M API, performs a scene search for 
Landsat 8 images over a specified location with limited cloud cover, and prints 
the results.
