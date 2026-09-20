import requests

def parse_api_response(resp):
    try:
        return resp.json()
    except ValueError:
        return {"error": "invalid json"}
