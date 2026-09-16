import pytest
import warnings
import click
from cli_helper import parse_command_args

def test_parse_command_args():
    @click.command()
    @click.option("--output", "-o")
    def sample_cmd(output):
        pass

    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        res = parse_command_args(sample_cmd, ["--output", "results.csv"])
        assert res.get("output") == "results.csv"

        dep_warnings = [w for w in recorded if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) == 0, f"Encountered deprecated call: {dep_warnings}"
