from starlette.staticfiles import StaticFiles

def is_etag_not_modified(etag: str, if_none_match: str) -> bool:
    sf = StaticFiles(directory=".")
    return sf.is_not_modified({"etag": etag}, {"if-none-match": if_none_match})
