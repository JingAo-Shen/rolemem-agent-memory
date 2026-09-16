import pytest
import warnings
from flask import Flask
from error_policy import configure_error_policy

class CustomTransientError(Exception):
    pass

def test_error_policy():
    app = Flask("err_app")
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        configure_error_policy(app, CustomTransientError)
        res = app.handle_exception(CustomTransientError("db glitch"))
        assert res is not None

        dep_warnings = [w for w in recorded if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) == 0, f"Encountered deprecated call: {dep_warnings}"
