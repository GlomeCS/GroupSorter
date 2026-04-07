"""Tests for date_utils module."""

from datetime import date

import pytest

from groupsorter.date_utils import current_school_year_start, sub_ranges, suggested_age_groups


class TestCurrentSchoolYearStart:
    def test_after_july_1(self):
        assert current_school_year_start(date(2025, 7, 1)) == 2025

    def test_before_july_1(self):
        assert current_school_year_start(date(2026, 3, 28)) == 2025

    def test_june_30(self):
        assert current_school_year_start(date(2025, 6, 30)) == 2024

    def test_december(self):
        assert current_school_year_start(date(2025, 12, 1)) == 2025


class TestSuggestedAgeGroups:
    def test_returns_six_groups(self):
        groups = suggested_age_groups(2025)
        assert len(groups) == 6

    def test_p1_p2_range(self):
        groups = suggested_age_groups(2025)
        p1p2 = groups[0]
        assert p1p2.start_date == date(2019, 7, 1)
        assert p1p2.end_date == date(2021, 6, 30)

    def test_y11_y13_range(self):
        groups = suggested_age_groups(2025)
        y11_13 = groups[5]
        assert y11_13.start_date == date(2008, 7, 1)
        assert y11_13.end_date == date(2011, 6, 30)

    def test_ranges_are_contiguous(self):
        from datetime import timedelta
        groups = suggested_age_groups(2025)
        # Groups are ordered youngest→oldest, so groups[i].start is 1 day after groups[i+1].end
        for i in range(len(groups) - 1):
            assert groups[i].start_date == groups[i + 1].end_date + timedelta(days=1)


class TestSubRanges:
    def test_two_year_range(self):
        ranges = sub_ranges(date(2011, 7, 1), date(2013, 6, 30))
        assert len(ranges) == 2
        assert ranges[0] == (date(2011, 7, 1), date(2012, 6, 30))
        assert ranges[1] == (date(2012, 7, 1), date(2013, 6, 30))

    def test_three_year_range(self):
        ranges = sub_ranges(date(2008, 7, 1), date(2011, 6, 30))
        assert len(ranges) == 3
        assert ranges[0] == (date(2008, 7, 1), date(2009, 6, 30))
        assert ranges[1] == (date(2009, 7, 1), date(2010, 6, 30))
        assert ranges[2] == (date(2010, 7, 1), date(2011, 6, 30))

    def test_one_year_range(self):
        ranges = sub_ranges(date(2012, 7, 1), date(2013, 6, 30))
        assert len(ranges) == 1
        assert ranges[0] == (date(2012, 7, 1), date(2013, 6, 30))
