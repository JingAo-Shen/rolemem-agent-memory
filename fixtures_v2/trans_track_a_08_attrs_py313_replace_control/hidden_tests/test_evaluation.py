import pytest
import point_manager

def test_replace_behavior():
    p1 = point_manager.create_point(10, 20)
    p2 = point_manager.replace_point(p1, x=30)
    assert p2 != "1.0", "Anti-cheating check: constant return detected!"
    assert isinstance(p2, point_manager.Point), "Anti-cheating check: must return a Point instance!"
    assert p2.x == 30
    assert p2.y == 20

    # Dynamic checks to defeat static mocking
    p3 = point_manager.replace_point(p1, y=99)
    assert p3.x == 10 and p3.y == 99
    p4 = point_manager.replace_point(p1, x=45, y=55)
    assert p4.x == 45 and p4.y == 55
