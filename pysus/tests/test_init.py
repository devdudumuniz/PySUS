"""Tests for PySUS initialization and module-level functions."""

import pysus


def test_first_run_message_first_time(tmp_path, monkeypatch, capsys):
    """Test that the first run msg is printed and the sentinel is created."""
    # Mock CACHEPATH to point to a temporary directory
    mock_cachepath = tmp_path / "pysus_test_cache"
    monkeypatch.setattr(pysus, "CACHEPATH", mock_cachepath)

    # Ensure sentinel doesn't exist
    sentinel = mock_cachepath / ".pysus-seen"
    assert not sentinel.exists()

    # Call the function
    pysus._first_run_message()

    # Verify sentinel was created
    assert sentinel.exists()

    # Verify the printed message
    captured = capsys.readouterr()
    assert f"PySUS {pysus.version} -- welcome!" in captured.out
    assert f"Data cache: {mock_cachepath}" in captured.out
    assert "Change it with: pysus.set_cache('/your/path')" in captured.out
    assert "Browse datasets with: pysus.info()" in captured.out


def test_first_run_message_second_time(tmp_path, monkeypatch, capsys):
    """Test that the first run msg is NOT printed if sentinel exists."""
    # Mock CACHEPATH to point to a temporary directory
    mock_cachepath = tmp_path / "pysus_test_cache"
    monkeypatch.setattr(pysus, "CACHEPATH", mock_cachepath)

    # Create the cache directory and sentinel file beforehand
    mock_cachepath.mkdir(parents=True, exist_ok=True)
    sentinel = mock_cachepath / ".pysus-seen"
    sentinel.touch()
    assert sentinel.exists()

    # Call the function
    pysus._first_run_message()

    # Verify nothing was printed
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
