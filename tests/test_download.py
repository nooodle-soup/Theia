import os
import sys
from theia.api import TheiaAPI


def test_download():
    # Set up the credentials and parameters for testing
    username = "nooodle-soup"
    password = "USGS@17032402"
    dataset_name = "landsat_tm_c2_l1"
    # Replace with valid scene IDs
    scene_ids = ["LT50380372012126EDC00"]
    download_path = "./downloads"  # Specify the download directory

    # Ensure the download path exists
    os.makedirs(download_path, exist_ok=True)

    # Initialize the API with credentials
    api = TheiaAPI(username=username, password=password)

    try:
        # Run the scene search
        api.download_scene(
            scene_ids=scene_ids,
            dataset_name=dataset_name,
            path=download_path,
            list_id="my_list",
        )

        print("Test download completed successfully.")

        # Check if the files have been downloaded
        downloaded_files = os.listdir(download_path)
        assert len(downloaded_files) > 0, "No files were downloaded."

        print(f"Downloaded files: {downloaded_files}")

    except Exception as e:
        print(f"Test download failed: {e}")

    api.logout()
    return


if __name__ == "__main__":
    test_download()
    print("here")
