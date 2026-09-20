import pytest
import asyncio
import async_helper

async def t_ok():
    return "ok_result"

async def t_err():
    raise RuntimeError("task_failure")

def test_gather():
    results = async_helper.run_gather_tasks([t_ok(), t_err()])
    assert results[0] == "ok_result"
    assert isinstance(results[1], RuntimeError)
