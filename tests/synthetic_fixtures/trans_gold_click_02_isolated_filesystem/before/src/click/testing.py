import tempfile
import contextlib
import os

class CliRunner:
    @contextlib.contextmanager
    def isolated_filesystem(self):
        with tempfile.TemporaryDirectory() as d:
            orig = os.getcwd()
            os.chdir(d)
            try:
                yield d
            finally:
                os.chdir(orig)
