"""Tests for pysus.api.metadata.cache module."""

from datetime import timedelta

from pysus.api.metadata.cache import (
    cache_size,
    clear_cache,
    get_cached_metadata,
    invalidate_metadata,
    set_cached_metadata,
)


def setup_function():
    """Clear cache before each test."""
    clear_cache()


def test_set_and_get():
    """Test basic set/get roundtrip."""
    metadata = {"columns": ["a", "b", "c"], "count": 100}
    set_cached_metadata("test:roundtrip", metadata)
    result = get_cached_metadata("test:roundtrip")
    assert result == metadata


def test_get_missing_returns_none():
    """Test that missing key returns None."""
    result = get_cached_metadata("nonexistent:key")
    assert result is None


def test_ttl_expiry():
    """Test that expired entries return None."""
    set_cached_metadata("test:ttl", {"data": 1})
    # Use very short TTL
    result = get_cached_metadata("test:ttl", ttl=timedelta(seconds=-1))
    assert result is None


def test_invalidate():
    """Test cache invalidation."""
    set_cached_metadata("test:invalidate", {"data": 1})
    assert get_cached_metadata("test:invalidate") is not None

    removed = invalidate_metadata("test:invalidate")
    assert removed is True
    assert get_cached_metadata("test:invalidate") is None


def test_invalidate_nonexistent():
    """Test invalidating a key that doesn't exist."""
    removed = invalidate_metadata("nonexistent:key")
    assert removed is False


def test_clear_cache():
    """Test clearing all cache entries."""
    set_cached_metadata("test:a", {"data": 1})
    set_cached_metadata("test:b", {"data": 2})
    assert cache_size() > 0

    count = clear_cache()
    assert count >= 2
    assert cache_size() == 0


def test_cache_size(monkeypatch, tmp_path):
    """Test cache size tracking."""
    import pysus.api.metadata.cache

    mock_cache_dir = tmp_path / ".cache" / "pysus" / "metadata"
    monkeypatch.setattr(pysus.api.metadata.cache, "_CACHE_DIR", mock_cache_dir)

    # Test when directory doesn't exist
    assert cache_size() == 0

    # Create directory and files
    mock_cache_dir.mkdir(parents=True)

    file1 = mock_cache_dir / "1.json"
    file1.write_text("a" * 10)  # 10 bytes

    file2 = mock_cache_dir / "2.json"
    file2.write_text("b" * 20)  # 20 bytes

    # Ignore non-json files
    file3 = mock_cache_dir / "3.txt"
    file3.write_text("c" * 30)

    assert cache_size() == 30


def test_corrupted_cache_returns_none():
    """Test that corrupted cache file returns None."""
    from pysus.api.metadata.cache import _cache_path

    cache_file = _cache_path("test:corrupted")
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text("not valid json")

    result = get_cached_metadata("test:corrupted")
    assert result is None


def test_unicode_metadata():
    """Test caching Unicode metadata."""
    metadata = {"name": "Município de São Paulo", "value": "R$ 1.000,00"}
    set_cached_metadata("test:unicode", metadata)
    result = get_cached_metadata("test:unicode")
    assert result == metadata


def test_nested_metadata():
    """Test caching nested metadata structures."""
    metadata = {
        "columns": {
            "DT_NOTIFIC": {"type": "string", "description": "Data"},
        },
        "groups": ["arboviroses", "dengue"],
    }
    set_cached_metadata("test:nested", metadata)
    result = get_cached_metadata("test:nested")
    assert result == metadata
