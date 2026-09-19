import httpx

def build_proxied_client(proxy_url: str):
    # Valid: passes modern proxy argument
    return httpx.Client(proxy=proxy_url)
