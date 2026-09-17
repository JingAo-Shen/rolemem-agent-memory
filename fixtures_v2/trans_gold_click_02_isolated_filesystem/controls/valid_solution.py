import pathlib

def setup_test_workspace(tmp_path):
    # Modern pattern: uses pytest tmp_path directly without deprecated isolated_filesystem
    test_dir = pathlib.Path(tmp_path) / "workspace"
    test_dir.mkdir(parents=True, exist_ok=True)
    return test_dir
