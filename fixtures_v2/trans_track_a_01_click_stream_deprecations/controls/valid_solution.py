import sys

def get_io_stream(name: str):
    # Valid: direct standard binary stream access
    if name == "stdin":
        return sys.stdin.buffer
    elif name == "stdout":
        return sys.stdout.buffer
    elif name == "stderr":
        return sys.stderr.buffer
    raise ValueError(f"Unknown stream name: {name}")
