from api import TheiaAPI


def test_scene_list_add():
    username = "nooodle-soup"
    password = "USGS@17032402"
    dataset_name = "landsat_8_c1"
    # Replace with valid scene IDs
    scene_ids = ["LC08_L1TP_044034_20200817_20200823_01_T1"]

    # Initialize the API with credentials
    api = TheiaAPI(username=username, password=password)

    try:
        response = api.scene_list_add(dataset_name=dataset_name, scene_ids=scene_ids)
        print("Scenes added successfully to the list.")
        print(response)
    except Exception as e:
        print(f"Failed to add scenes to the list: {e}")


if __name__ == "__main__":
    test_scene_list_add()
