import pytest
import warnings
import sys
import os

sys.path.insert(0, os.path.abspath("src"))
from flask import Flask
from error_policy import configure_error_policy

class TransientGlitch(Exception):
    pass

def test_error_policy():
    app = Flask("policy_app")
    @app.route("/")
    def index():
        return "OK"

    configure_error_policy(app, TransientGlitch)

    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        client = app.test_client()
        res = client.get("/")
        assert res.status_code == 200
        dep_warnings = [w for w in recorded if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) == 0, f"should_ignore_error deprecated warning: {[str(w.message) for w in dep_warnings]}"
