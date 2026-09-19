import itsdangerous

def get_package_version() -> str:
    # Stale: accessing removed __version__
    return itsdangerous.__version__
