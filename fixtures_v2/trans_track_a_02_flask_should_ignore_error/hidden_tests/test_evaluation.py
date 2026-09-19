import pytest
import warnings
import custom_app

def test_flask_custom_app_dispatch():
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        app = custom_app.CustomApp("test_app")
        @app.route("/")
        def index():
            return "ok"
        client = app.test_client()
        res = client.get("/")
        assert res.status_code == 200
