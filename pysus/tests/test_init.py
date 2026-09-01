from importlib import metadata as importlib_metadata
from unittest.mock import patch

from pysus import get_version


def test_get_version_success():
    """Test get_version when the package is found."""
    with patch("pysus.importlib_metadata.version", return_value="1.2.3"):
        assert get_version() == "1.2.3"


def test_get_version_package_not_found():
    """Test get_version when the package is not found (PackageNotFoundError is raised)."""
    with patch(
        "pysus.importlib_metadata.version",
        side_effect=importlib_metadata.PackageNotFoundError,
    ):
        # When PackageNotFoundError is raised, it should fallback to the hardcoded version
        assert get_version() == "2.10.6"
