import pytest
import config_reader

def test_read_config_strips_comments():
    data = "[settings]\ntimeout = 30 # connection timeout\n"
    assert config_reader.read_config_value(data, "settings", "timeout") == "30"
