import pytest
from flask import Flask
from ctx_manager import activate_application_context

def test_activate_application_context():
    app = Flask("test_isolated_app")
    ctx = activate_application_context(app)
    from flask.globals import _app_ctx_stack
    assert _app_ctx_stack.top is not None
    assert _app_ctx_stack.top.app.name == "test_isolated_app"
    ctx.pop()
