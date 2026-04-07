"""Tests for excel_io parsing helpers."""

from datetime import date, datetime

from groupsorter.excel_io import _parse_dob


class TestParseDob:
    def test_none_returns_none(self):
        assert _parse_dob(None) == (None, "")

    def test_datetime_object(self):
        dt = datetime(2010, 5, 15, 12, 0)
        d, raw = _parse_dob(dt)
        assert d == date(2010, 5, 15)

    def test_date_object(self):
        d_in = date(2010, 5, 15)
        d, raw = _parse_dob(d_in)
        assert d == d_in
        assert raw == str(d_in)

    def test_iso_format(self):
        d, raw = _parse_dob("2010-05-15")
        assert d == date(2010, 5, 15)
        assert raw == "2010-05-15"

    def test_uk_slash_format(self):
        d, raw = _parse_dob("15/05/2010")
        assert d == date(2010, 5, 15)

    def test_uk_dash_format(self):
        d, raw = _parse_dob("15-05-2010")
        assert d == date(2010, 5, 15)

    def test_short_month_name_format(self):
        d, raw = _parse_dob("15 Jan 2010")
        assert d == date(2010, 1, 15)

    def test_long_month_name_format(self):
        d, raw = _parse_dob("15 January 2010")
        assert d == date(2010, 1, 15)

    def test_unparseable_returns_none(self):
        d, raw = _parse_dob("not a date")
        assert d is None
        assert raw == "not a date"

    def test_empty_string_returns_none(self):
        d, raw = _parse_dob("")
        assert d is None
        assert raw == ""

    def test_us_format_not_accepted(self):
        # %m/%d/%Y was removed; MM/DD/YYYY strings must fail gracefully
        # A value like "13/01/2010" is unambiguously DD/MM/YYYY (day=13)
        d, raw = _parse_dob("13/01/2010")
        assert d == date(2010, 1, 13)

    def test_ambiguous_slash_date_parsed_as_uk(self):
        # "01/02/2010" is ambiguous; we parse DD/MM/YYYY first → 1 Feb 2010
        d, raw = _parse_dob("01/02/2010")
        assert d == date(2010, 2, 1)
