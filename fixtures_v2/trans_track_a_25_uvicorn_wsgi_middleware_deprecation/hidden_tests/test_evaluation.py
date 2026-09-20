import pytest
import warnings
from uvicorn.middleware.wsgi import WSGIMiddleware
import wsgi_inspector

def sample_app(environ, start_response):
    start_response("200 OK", [])
    return [b""]

def test_wsgi_status():
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        mw = wsgi_inspector.wrap_wsgi_application(sample_app)
        assert isinstance(mw, WSGIMiddleware)
        assert mw.app is sample_app
