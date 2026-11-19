from importlib import metadata as importlib_metadata
from pathlib import Path
from unittest.mock import patch

import pysus


def test_get_version_from_installed_metadata():
    with patch("pysus.importlib_metadata.version", return_value="1.2.3"):
        assert pysus.get_version() == "1.2.3"


def test_get_version_fallback_matches_release_version():
    with patch(
        "pysus.importlib_metadata.version",
        side_effect=importlib_metadata.PackageNotFoundError,
    ):
        assert pysus.get_version() == pysus.__version__


def test_set_cache_creates_and_resolves_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(pysus, "CACHEPATH", tmp_path / "original")
    requested = tmp_path / "nested" / "cache"

    result = pysus.set_cache(requested)

    assert isinstance(result, Path)
    assert result == requested.resolve()
    assert result.is_dir()
    assert pysus.CACHEPATH == result


def test_first_run_message_creates_sentinel(tmp_path, monkeypatch, capsys):
    cache_path = tmp_path / "cache"
    monkeypatch.setattr(pysus, "CACHEPATH", cache_path)

    pysus._first_run_message()

    assert (cache_path / ".pysus-seen").is_file()
    output = capsys.readouterr().out
    assert f"PySUS {pysus.version} -- welcome!" in output
    assert f"Data cache: {cache_path}" in output


def test_first_run_message_is_silent_after_first_run(
    tmp_path, monkeypatch, capsys
):
    cache_path = tmp_path / "cache"
    cache_path.mkdir()
    (cache_path / ".pysus-seen").touch()
    monkeypatch.setattr(pysus, "CACHEPATH", cache_path)

    pysus._first_run_message()

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
