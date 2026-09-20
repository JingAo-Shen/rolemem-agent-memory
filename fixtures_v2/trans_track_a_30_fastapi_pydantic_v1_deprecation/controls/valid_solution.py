import inspect
import fastapi.dependencies.utils

def is_pydantic_v1_deprecated() -> bool:
    src = inspect.getsource(fastapi.dependencies.utils.get_dependant)
    assert "pydantic.v1 is deprecated" in src
    return True
