import pytest
from rich.console import Group
import group_factory

def test_create_render_group():
    grp = group_factory.create_render_group("item1", "item2")
    assert isinstance(grp, Group)
    assert list(grp.renderables) == ["item1", "item2"]
