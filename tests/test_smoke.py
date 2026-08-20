from importlib.metadata import version

import critaudit


def test_package_imports():
    assert critaudit.__version__ == "0.1.0"


def test_declared_version_matches_distribution_metadata():
    """`__version__` and pyproject's `version` are separate literals; pin them together
    so a release bump cannot land in one and silently drift in the other."""
    assert critaudit.__version__ == version("critaudit")
