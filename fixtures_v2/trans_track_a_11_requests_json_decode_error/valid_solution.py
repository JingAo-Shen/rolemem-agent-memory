import requests
from requests.exceptions import JSONDecodeError

def parse_api_response(resp):
    try:
        return resp.json()
    except JSONDecodeError:
        return {"error": "invalid json"}
