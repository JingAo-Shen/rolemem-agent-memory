import pytest
import flake8_config

def test_doctest_filtering():
    assert flake8_config.check_doctest_filtering() is True
