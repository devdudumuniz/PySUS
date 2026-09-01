"""Tests for pysus.api.metadata.cache."""

from pathlib import Path
import pytest

from pysus.api.metadata.cache import clear_cache

@pytest.fixture
def mock_cache_dir(tmp_path, monkeypatch):
    """Mock the _CACHE_DIR to a temporary path."""
    monkeypatch.setattr("pysus.api.metadata.cache._CACHE_DIR", tmp_path)
    return tmp_path

def test_clear_cache_dir_not_exists(tmp_path, monkeypatch):
    """Test clear_cache when cache directory does not exist."""
    non_existent_dir = tmp_path / "non_existent"
    monkeypatch.setattr("pysus.api.metadata.cache._CACHE_DIR", non_existent_dir)
    assert clear_cache() == 0

def test_clear_cache_empty_dir(mock_cache_dir):
    """Test clear_cache when cache directory is empty."""
    assert clear_cache() == 0

def test_clear_cache_with_json_files(mock_cache_dir):
    """Test clear_cache removes JSON files and returns correct count."""
    # Create some JSON files
    (mock_cache_dir / "test1.json").write_text("{}")
    (mock_cache_dir / "test2.json").write_text("{}")

    assert clear_cache() == 2
    assert not (mock_cache_dir / "test1.json").exists()
    assert not (mock_cache_dir / "test2.json").exists()

def test_clear_cache_ignores_non_json_files(mock_cache_dir):
    """Test clear_cache only removes JSON files."""
    # Create a JSON file and a non-JSON file
    (mock_cache_dir / "test.json").write_text("{}")
    (mock_cache_dir / "test.txt").write_text("not json")

    assert clear_cache() == 1
    assert not (mock_cache_dir / "test.json").exists()
    assert (mock_cache_dir / "test.txt").exists()
