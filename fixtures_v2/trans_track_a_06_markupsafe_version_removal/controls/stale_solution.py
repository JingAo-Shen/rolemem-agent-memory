import markupsafe

def get_library_version() -> str:
    # Stale: accessing removed __version__
    return markupsafe.__version__
