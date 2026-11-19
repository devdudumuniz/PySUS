"""pytest configuration - mocks duckdb.functional before any other imports.

Also silences the flat-API deprecation warning globally; dedicated tests
assert it fires by re-enabling it with ``warnings.catch_warnings`` /
``simplefilter("always")``.
"""

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

if "duckdb.functional" not in sys.modules:
    _mock = MagicMock()
    _mock.SPECIAL = "SPECIAL"
    sys.modules["duckdb.functional"] = _mock


@pytest.fixture
def offline_ducklake(monkeypatch):
    """Isolate orchestrator tests from the live catalog download.

    Only tests that explicitly request this fixture use it. Dedicated
    DuckLake/catalog adapter tests still exercise their own mocked transports.
    """
    monkeypatch.setattr("pysus.api.client.DuckLake.connect", AsyncMock())


def pytest_configure(config):
    import warnings

    from pysus.api.errors import PySUSWarning

    warnings.filterwarnings("ignore", category=PySUSWarning)
