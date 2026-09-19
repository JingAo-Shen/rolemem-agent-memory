import pytest
import warnings
import custom_app
from flask import Flask

def test_flask_custom_app_dispatch():
    assert issubclass(custom_app.CustomApp, Flask), "Anti-cheating check: CustomApp must be a Flask subclass!"

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        app = custom_app.CustomApp("test_app")
        assert app != "1.0", "Anti-cheating check: constant return detected!"
        @app.route("/")
        def index():
            return "ok"
        client = app.test_client()
        res = client.get("/")
        assert res.status_code == 200
        assert res.data == b"ok"
