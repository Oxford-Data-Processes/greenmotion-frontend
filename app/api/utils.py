import requests

BASE_URL = "https://zhjlsusdz3.execute-api.eu-west-2.amazonaws.com/prod/"


def get_request(api_url):
    full_url = f"{BASE_URL.rstrip('/')}{api_url}"

    try:
        response = requests.get(full_url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        raise e
