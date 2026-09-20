import pytest
import pair_helper

def test_pair_strictly():
    assert pair_helper.pair_strictly([1, 2], ["a", "b"]) == [(1, "a"), (2, "b")]
    with pytest.raises(ValueError):
        pair_helper.pair_strictly([1, 2, 3], ["a", "b"])
