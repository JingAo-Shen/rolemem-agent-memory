import pytest
import tz_checker

def test_tz_warning_name():
    assert tz_checker.get_tz_warning_name() == "UnknownTimezoneWarning"
