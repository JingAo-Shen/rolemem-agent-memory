import httpx

def build_proxied_client(proxy_url: str):
    # Stale: passes deprecated proxies argument
    return httpx.Client(proxies={"http://": proxy_url})
