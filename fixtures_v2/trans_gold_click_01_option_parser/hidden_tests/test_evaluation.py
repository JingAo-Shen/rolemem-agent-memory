import pytest
import warnings
import sys
import os

sys.path.insert(0, os.path.abspath("src"))
import click

def test_parse_args():
    @click.command()
    @click.option("--name", default="World")
    def hello(name):
        pass

    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        from cli_helper import parse_command_args
        res = parse_command_args(hello, ["--name", "Antigravity"])
        assert res.get("name") == "Antigravity"
        dep_warnings = [w for w in recorded if issubclass(w.category, (DeprecationWarning, UserWarning))]
        assert len(dep_warnings) == 0, f"OptionParser deprecated: {[str(w.message) for w in dep_warnings]}"
