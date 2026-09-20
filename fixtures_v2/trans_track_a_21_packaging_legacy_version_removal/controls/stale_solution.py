from packaging.version import LegacyVersion

def parse_version_safely(v: str) -> str:
    # Stale implementation using removed LegacyVersion
    return str(LegacyVersion(v))
