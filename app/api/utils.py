import requests

BASE_URL = "https://zhjlsusdz3.execute-api.eu-west-2.amazonaws.com/prod/"

# BASE_URL = "http://localhost:8000/"


def get_request(api_url):
    # Combine base URL with the endpoint
    full_url = BASE_URL.rstrip('/') + api_url
    
    try:
        response = requests.get(full_url)
        response.raise_for_status()  # Raises an HTTPError for bad status codes
        
        return response.json()
        
    except requests.exceptions.HTTPError as e:
        if response.status_code == 500:
            print(f"Server error (500) for URL: {full_url}")
            print(f"Response content: {response.text}")
        else:
            print(f"HTTP Error: {e}")
        return None
        
    except ValueError as e:
        print(f"Failed to decode JSON from API response: {str(e)}")
        print(f"Status code: {response.status_code}")
        print(f"Response content: {response.text}")
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {str(e)}")
        return None
