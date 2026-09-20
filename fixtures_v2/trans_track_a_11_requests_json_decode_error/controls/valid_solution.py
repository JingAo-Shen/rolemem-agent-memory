from requests.exceptions import RequestException

def parse_api_response(resp):
    try:
        return resp.json()
    except RequestException:
        return {"error": "invalid json"}
