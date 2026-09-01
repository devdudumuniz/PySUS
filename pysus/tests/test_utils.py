import pytest
from unittest.mock import patch
from pysus.utils import zfill_year

def test_zfill_year():
    with patch('pysus.utils.datetime') as mock_datetime:
        mock_datetime.datetime.now.return_value.year = 2024

        # Test 2-digit years <= current year (24) -> 20xx
        assert zfill_year(20) == 2020
        assert zfill_year(24) == 2024
        assert zfill_year('05') == 2005
        assert zfill_year(5) == 2005

        # Test 2-digit years > current year (24) -> 19xx
        assert zfill_year(25) == 1925
        assert zfill_year(99) == 1999
        assert zfill_year('99') == 1999

        # Test 4-digit years (should still look at last 2 digits for now based on implementation)
        # 1999 -> 99 > 24 -> 1999
        assert zfill_year(1999) == 1999
        # 2020 -> 20 <= 24 -> 2020
        assert zfill_year(2020) == 2020
