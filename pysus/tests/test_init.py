import pathlib

import pysus


def test_set_cache(tmp_path):
    # Call set_cache with tmp_path
    new_cache = pysus.set_cache(tmp_path)

    # Assert return value is a resolved Path object pointing to tmp_path
    assert isinstance(new_cache, pathlib.Path)
    assert new_cache == tmp_path.resolve()

    # Assert directory is created
    assert new_cache.exists()
    assert new_cache.is_dir()

    # Assert global CACHEPATH is updated
    assert pysus.CACHEPATH == tmp_path.resolve()

    # Test setting a sub-directory that does not exist yet
    sub_dir = tmp_path / "sub" / "dir"
    new_cache2 = pysus.set_cache(sub_dir)
    assert new_cache2 == sub_dir.resolve()
    assert new_cache2.exists()
    assert pysus.CACHEPATH == sub_dir.resolve()
