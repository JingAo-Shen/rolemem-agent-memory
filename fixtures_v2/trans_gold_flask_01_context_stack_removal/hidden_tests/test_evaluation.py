import pytest
import sys
import os

sys.path.insert(0, os.path.abspath("src"))
from flask import Flask, current_app
from ctx_manager import activate_application_context

def test_activate_ctx():
    app = Flask("test_isolated_app")
    ctx = activate_application_context(app)
    assert current_app.name == "test_isolated_app"
    ctx.pop()
