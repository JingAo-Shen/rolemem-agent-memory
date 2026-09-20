import pytest
import app_lifecycle

def test_default_lifespan():
    assert app_lifecycle.has_default_lifespan() is True
