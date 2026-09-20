from packaging.version import Version

def parse_version_safely(v: str) -> str:
    return str(Version(v))
