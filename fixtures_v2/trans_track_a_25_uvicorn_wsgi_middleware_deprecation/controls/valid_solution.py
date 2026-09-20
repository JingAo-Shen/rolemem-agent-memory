import warnings
from uvicorn.middleware.wsgi import WSGIMiddleware

def wrap_wsgi_application(app):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return WSGIMiddleware(app)
