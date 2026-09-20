import pytest
from starlette.middleware.exceptions import ExceptionMiddleware
import exception_handler

async def dummy_app(scope, receive, send):
    pass

def test_build():
    mw = exception_handler.build_exception_middleware(dummy_app)
    assert isinstance(mw, ExceptionMiddleware)
