import requests

# Define the base URL of your FastAPI application
BASE_URL = "http://127.0.0.1:8000"


# Generic function to perform a GET request
def get_request(endpoint, params=None):
    response = requests.get(f"{BASE_URL}{endpoint}", params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to call {endpoint}: {response.status_code}")
        return None


# Generic function to perform a POST request
def post_request(endpoint, json_data=None):
    response = requests.post(f"{BASE_URL}{endpoint}", json=json_data)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to call {endpoint}: {response.status_code}")
        return None
