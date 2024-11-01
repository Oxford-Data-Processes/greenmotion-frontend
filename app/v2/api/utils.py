import requests

BASE_URL = "https://t2ahwaivrk.execute-api.eu-west-2.amazonaws.com/dev"


def get_request(endpoint, params=None):
    response = requests.get(f"{BASE_URL}{endpoint}", params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to call {endpoint}: {response.status_code}")
