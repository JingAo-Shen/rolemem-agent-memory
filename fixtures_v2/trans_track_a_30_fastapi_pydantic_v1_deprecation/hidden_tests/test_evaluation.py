import pytest
import fastapi_pydantic_auditor

def test_pydantic_v1_deprecated():
    assert fastapi_pydantic_auditor.is_pydantic_v1_deprecated() is True
