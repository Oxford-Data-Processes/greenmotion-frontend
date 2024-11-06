import requests

BASE_URL = "https://zhjlsusdz3.execute-api.eu-west-2.amazonaws.com/dev/"

# BASE_URL = "http://localhost:8000/"


def get_request(endpoint, params=None):
    response = requests.get(f"{BASE_URL}{endpoint}", params=params)
    print("RESPONSE")
    print(response)
    return response.json()
