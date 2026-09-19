import attr

@attr.s(auto_attribs=True)
class Point:
    x: int
    y: int

def create_point(x: int, y: int) -> Point:
    return Point(x, y)

def replace_point(pt: Point, **changes) -> Point:
    # Stale: uses evolve explicitly
    return attr.evolve(pt, **changes)
