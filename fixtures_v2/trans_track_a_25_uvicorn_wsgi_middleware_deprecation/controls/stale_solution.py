from uvicorn.middleware.wsgi import WSGIMiddleware

def wrap_wsgi_application(app):
    return WSGIMiddleware(app)
