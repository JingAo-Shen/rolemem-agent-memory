import click.utils

def get_io_stream(name: str):
    # Stale: uses deprecated get_binary_stream
    return click.utils.get_binary_stream(name)
