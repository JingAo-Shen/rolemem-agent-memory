def normalize_etag(etag: str) -> str:
    if etag.startswith("W/"):
        return etag[2:]
    return etag
