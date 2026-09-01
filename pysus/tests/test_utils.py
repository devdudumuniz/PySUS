import datetime

from pysus import utils


class _FixedDatetime(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2024, 1, 1, tzinfo=tz)


def test_zfill_year_uses_current_century_cutoff(monkeypatch):
    monkeypatch.setattr(utils.datetime, "datetime", _FixedDatetime)

    assert utils.zfill_year(5) == 2005
    assert utils.zfill_year("24") == 2024
    assert utils.zfill_year(25) == 1925
    assert utils.zfill_year("99") == 1999
    assert utils.zfill_year(1999) == 1999
    assert utils.zfill_year(2020) == 2020
