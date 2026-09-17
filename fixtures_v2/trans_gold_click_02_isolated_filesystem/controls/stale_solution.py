from click.testing import CliRunner

def setup_test_workspace(tmp_path=None):
    runner = CliRunner()
    # Stale action: calls deprecated isolated_filesystem
    with runner.isolated_filesystem():
        return tmp_path or "/tmp"
