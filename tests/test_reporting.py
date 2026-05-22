"""Tests for reporting formatters."""

from datetime import date

from groupsorter.domain import Person
from groupsorter.reporting import (
    format_anomaly_report,
    format_excluded_report,
    format_gender_anomaly_report,
    format_groups_report,
)

START = date(2011, 7, 1)
END = date(2013, 6, 30)


def person(name: str, dob: date | None, gender: str | None = None, raw_gender: str = "") -> Person:
    return Person(name=name, dob=dob, gender=gender, raw_gender=raw_gender)


class TestFormatAnomalyReport:
    def test_no_anomalies(self):
        report = format_anomaly_report([], START, END)
        assert "No DOB anomalies" in report

    def test_lists_anomalous_names(self):
        p = person("OldPerson", date(2009, 1, 1))
        report = format_anomaly_report([p], START, END)
        assert "OldPerson" in report
        assert "1" in report

    def test_includes_expected_range(self):
        report = format_anomaly_report([person("X", None)], START, END)
        assert "2011" in report
        assert "2013" in report

    def test_missing_dob_shown_as_unreadable(self):
        p = Person(name="NoDOB", dob=None, raw_dob="???")
        report = format_anomaly_report([p], START, END)
        assert "???" in report


class TestFormatGenderAnomalyReport:
    def test_no_anomalies(self):
        report = format_gender_anomaly_report([])
        assert "No gender anomalies" in report

    def test_lists_anomalous_names(self):
        p = person("Unknown", date(2012, 5, 1))
        report = format_gender_anomaly_report([p])
        assert "Unknown" in report
        assert "1" in report

    def test_blank_gender_shows_missing(self):
        p = Person(name="Blank", dob=date(2012, 5, 1), gender=None, raw_gender="")
        report = format_gender_anomaly_report([p])
        assert "(missing)" in report

    def test_unrecognised_gender_shows_raw_value(self):
        p = Person(name="Mx", dob=date(2012, 5, 1), gender=None, raw_gender="NONBINARY")
        report = format_gender_anomaly_report([p])
        assert "NONBINARY" in report
        assert "unrecognised" in report


class TestFormatGroupsReport:
    def test_mixed_mode_label(self):
        report = format_groups_report([[person("A", date(2012, 1, 1))]], "mixed")
        assert "Mixed" in report

    def test_isolated_mode_label(self):
        report = format_groups_report([[person("A", date(2012, 1, 1))]], "isolated")
        assert "Isolated" in report

    def test_fell_back_label(self):
        report = format_groups_report([[person("A", date(2012, 1, 1))]], "isolated", fell_back=True)
        assert "fell back" in report

    def test_group_count_shown(self):
        groups = [[person("A", date(2012, 1, 1))], [person("B", date(2012, 2, 1))]]
        report = format_groups_report(groups, "mixed")
        assert "Groups: 2" in report

    def test_empty_group_shown(self):
        report = format_groups_report([[], [person("A", date(2012, 1, 1))]], "mixed")
        assert "(empty)" in report

    def test_gender_mixed_label(self):
        report = format_groups_report([], "mixed", gender_mode="mixed")
        assert "Gender sort mode: Mixed" in report

    def test_gender_isolated_label(self):
        report = format_groups_report([], "mixed", gender_mode="isolated")
        assert "Gender sort mode: Isolated" in report


class TestFormatExcludedReport:
    def test_empty_when_no_exclusions(self):
        assert format_excluded_report([], []) == ""

    def test_dob_anomalies_shown(self):
        p = person("OldPerson", date(2009, 1, 1))
        report = format_excluded_report([p], [])
        assert "OldPerson" in report
        assert "DOB" in report

    def test_gender_anomalies_shown(self):
        p = Person(name="NoGender", dob=date(2012, 1, 1), gender=None, raw_gender="")
        report = format_excluded_report([], [p])
        assert "NoGender" in report
        assert "gender" in report

    def test_both_sections_present(self):
        dob_p = person("Old", date(2009, 1, 1))
        gen_p = Person(name="NoG", dob=date(2012, 1, 1), gender=None, raw_gender="X")
        report = format_excluded_report([dob_p], [gen_p])
        assert "Old" in report
        assert "NoG" in report
