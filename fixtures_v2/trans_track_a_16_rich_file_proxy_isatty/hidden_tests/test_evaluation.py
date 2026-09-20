import io
import pytest
import proxy_checker
from rich.file_proxy import FileProxy
from rich.console import Console

class DummyTTY(io.StringIO):
    def isatty(self):
        return True

def test_proxy_interactive():
    console = Console()
    f = DummyTTY()
    proxy = FileProxy(console, f)
    assert proxy_checker.check_proxy_interactive(proxy) is True
