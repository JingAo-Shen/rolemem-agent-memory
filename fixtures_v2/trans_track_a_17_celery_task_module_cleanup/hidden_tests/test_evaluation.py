import pytest
import task_helper

def test_task_export():
    assert task_helper.check_task_export() is True
