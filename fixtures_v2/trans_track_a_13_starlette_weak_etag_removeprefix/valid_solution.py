def normalize_etag(etag: str) -> str:
    return etag.removeprefix("W/")
