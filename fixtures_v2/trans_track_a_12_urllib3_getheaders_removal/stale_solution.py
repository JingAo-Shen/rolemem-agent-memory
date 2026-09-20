def get_header_content_type(resp):
    for k, v in resp.getheaders():
        if k.lower() == "content-type":
            return v
    return None
