import importlib.metadata
from unittest import mock
from pysus import get_version

def test_get_version_success():
    with mock.patch("pysus.importlib_metadata.version", return_value="1.2.3"):
        assert get_version() == "1.2.3"

def test_get_version_fallback():
    with mock.patch(
        "pysus.importlib_metadata.version",
        side_effect=importlib.metadata.PackageNotFoundError
    ):
        assert get_version() == "2.10.6"
