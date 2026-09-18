import pytest

def validate_task_spec_for_handoff(spec: dict) -> str:
    """Validates transition spec for handoff execution and extracts current_task."""
    if "current_task" not in spec:
        raise ValueError("TASK_SCHEMA_ERROR: 'current_task' field is missing from transition spec.")
    task_prompt = spec["current_task"]
    if not isinstance(task_prompt, str) or not task_prompt.strip():
        raise ValueError("TASK_SCHEMA_ERROR: 'current_task' must be a non-empty string.")
    return task_prompt.strip()


def test_handoff_schema_success():
    spec = {"current_task": "Implement `clean_url(url)` in `utils.py`."}
    prompt = validate_task_spec_for_handoff(spec)
    assert prompt == "Implement `clean_url(url)` in `utils.py`."


def test_handoff_schema_missing_current_task_hard_fails():
    spec = {"task_instruction": "Some task instruction"}
    with pytest.raises(ValueError) as exc_info:
        validate_task_spec_for_handoff(spec)
    assert "TASK_SCHEMA_ERROR" in str(exc_info.value)
    assert "missing" in str(exc_info.value)


def test_handoff_schema_empty_current_task_hard_fails():
    spec = {"current_task": "   "}
    with pytest.raises(ValueError) as exc_info:
        validate_task_spec_for_handoff(spec)
    assert "TASK_SCHEMA_ERROR" in str(exc_info.value)
    assert "non-empty" in str(exc_info.value)
