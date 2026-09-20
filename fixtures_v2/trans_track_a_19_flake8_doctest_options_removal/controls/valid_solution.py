from flake8.plugins.pyflakes import FlakesChecker

def check_doctest_filtering():
    return hasattr(FlakesChecker, "with_doctest")
