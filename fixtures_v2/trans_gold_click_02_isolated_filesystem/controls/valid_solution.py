import tempfile
import os

def run_in_isolated_dir(task_fn):
    # Valid pattern: tempfile.TemporaryDirectory
    with tempfile.TemporaryDirectory() as tmp_dir:
        orig = os.getcwd()
        try:
            os.chdir(tmp_dir)
            return task_fn()
        finally:
            os.chdir(orig)
