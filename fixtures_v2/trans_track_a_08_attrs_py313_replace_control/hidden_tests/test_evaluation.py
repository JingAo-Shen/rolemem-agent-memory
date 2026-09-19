import pytest
import point_manager

def test_replace_behavior():
    p1 = point_manager.create_point(10, 20)
    p2 = point_manager.replace_point(p1, x=30)
    assert p2.x == 30
    assert p2.y == 20
