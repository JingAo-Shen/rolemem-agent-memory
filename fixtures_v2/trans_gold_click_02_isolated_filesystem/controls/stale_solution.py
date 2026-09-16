from click.testing import CliRunner

def run_in_isolated_dir(task_fn):
    # Stale pattern: CliRunner.isolated_filesystem is deprecated (PR #3704)
    runner = CliRunner()
    with runner.isolated_filesystem():
        return task_fn()
