import tempfile
import contextlib
import os
import warnings

class CliRunner:
    @contextlib.contextmanager
    def isolated_filesystem(self):
        warnings.warn(
            "'CliRunner.isolated_filesystem' is deprecated due to lack of thread safety. Use tempfile.TemporaryDirectory instead.",
            DeprecationWarning,
            stacklevel=2
        )
        with tempfile.TemporaryDirectory() as d:
            orig = os.getcwd()
            os.chdir(d)
            try:
                yield d
            finally:
                os.chdir(orig)
