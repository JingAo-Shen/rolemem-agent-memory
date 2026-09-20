import pytest
from datetime import timedelta
from cachelib.base import BaseCache
import cache_helper

def test_normalize():
    c = BaseCache(default_timeout=100)
    res = cache_helper.normalize_timeout_value(c, timedelta(minutes=10))
    assert res == 600
