def requires_pyvenv_patch(info) -> bool:
    # Valid: modern virtualenv does not require macOS Python 3.8 launcher patch
    return False
