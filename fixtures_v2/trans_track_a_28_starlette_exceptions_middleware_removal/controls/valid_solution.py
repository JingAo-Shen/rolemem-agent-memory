from starlette.middleware.exceptions import ExceptionMiddleware

def build_exception_middleware(app):
    return ExceptionMiddleware(app)
