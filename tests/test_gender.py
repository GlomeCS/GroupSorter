"""Tests for gender-aware sorting and anomaly detection."""

from datetime import date

from groupsorter.anomaly import Person, find_gender_anomalies, format_gender_anomaly_report
from groupsorter.excel_io import _parse_gender
from groupsorter.sorter import gender_allocation, sort_groups

START = date(2011, 7, 1)
END = date(2013, 6, 30)


def person(name: str, dob: date, gender: str | None = None) -> Person:
    return Person(name=name, dob=dob, gender=gender)


def make_people(n_male: int, n_female: int) -> list[Person]:
    people = []
    for i in range(n_male):
        people.append(person(f"M_{i}", date(2012, 1, i % 28 + 1), "M"))
    for i in range(n_female):
        people.append(person(f"F_{i}", date(2012, 6, i % 28 + 1), "F"))
    return people


# ---------------------------------------------------------------------------
# _parse_gender
# ---------------------------------------------------------------------------

class TestParseGender:
    def test_m(self):
        assert _parse_gender("M") == ("M", "M")

    def test_f(self):
        assert _parse_gender("F") == ("F", "F")

    def test_male_word(self):
        assert _parse_gender("male") == ("M", "male")

    def test_female_word(self):
        assert _parse_gender("FEMALE") == ("F", "FEMALE")

    def test_lowercase(self):
        assert _parse_gender("m") == ("M", "m")
        assert _parse_gender("f") == ("F", "f")

    def test_none_returns_none(self):
        normalised, raw = _parse_gender(None)
        assert normalised is None
        assert raw == ""

    def test_blank_returns_none(self):
        assert _parse_gender("")[0] is None
        assert _parse_gender("  ")[0] is None

    def test_unknown_returns_none_with_raw(self):
        normalised, raw = _parse_gender("X")
        assert normalised is None
        assert raw == "X"

    def test_unrecognised_preserves_raw(self):
        normalised, raw = _parse_gender("NONBINARY")
        assert normalised is None
        assert raw == "NONBINARY"


# ---------------------------------------------------------------------------
# find_gender_anomalies
# ---------------------------------------------------------------------------

class TestFindGenderAnomalies:
    def test_no_anomalies(self):
        people = make_people(3, 3)
        assert find_gender_anomalies(people) == []

    def test_missing_gender_flagged(self):
        p = person("NoGender", date(2012, 1, 1), None)
        result = find_gender_anomalies([p])
        assert p in result

    def test_valid_not_flagged(self):
        p = person("Alice", date(2012, 1, 1), "F")
        assert find_gender_anomalies([p]) == []

    def test_mixed_list(self):
        ok = person("Bob", date(2012, 1, 1), "M")
        bad = person("NoGender", date(2012, 3, 1), None)
        result = find_gender_anomalies([ok, bad])
        assert bad in result
        assert ok not in result


# ---------------------------------------------------------------------------
# format_gender_anomaly_report
# ---------------------------------------------------------------------------

class TestFormatGenderAnomalyReport:
    def test_no_anomalies(self):
        report = format_gender_anomaly_report([])
        assert "No gender anomalies" in report

    def test_lists_anomalous_names(self):
        p = person("Unknown", date(2012, 5, 1), None)
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


# ---------------------------------------------------------------------------
# gender_allocation
# ---------------------------------------------------------------------------

class TestGenderAllocation:
    def test_equal_split(self):
        people = make_people(10, 10)
        male_g, female_g = gender_allocation(people, 4)
        assert male_g == 2
        assert female_g == 2
        assert male_g + female_g == 4

    def test_proportional(self):
        people = make_people(9, 3)
        male_g, female_g = gender_allocation(people, 4)
        assert male_g > female_g
        assert male_g + female_g == 4

    def test_one_gender_empty(self):
        people = make_people(10, 0)
        male_g, female_g = gender_allocation(people, 4)
        assert male_g == 4
        assert female_g == 0


# ---------------------------------------------------------------------------
# sort_groups — gender_mode="isolated"
# ---------------------------------------------------------------------------

class TestGenderIsolated:
    def test_total_people_preserved(self):
        people = make_people(6, 6)
        groups = sort_groups(people, START, END, 4, "mixed", gender_mode="isolated")
        assert sum(len(g) for g in groups) == 12

    def test_correct_number_of_groups(self):
        people = make_people(6, 6)
        groups = sort_groups(people, START, END, 4, "mixed", gender_mode="isolated")
        assert len(groups) == 4

    def test_no_group_has_mixed_gender(self):
        people = make_people(8, 4)
        groups = sort_groups(people, START, END, 4, "mixed", gender_mode="isolated")
        for group in groups:
            if not group:
                continue
            genders = {p.gender for p in group}
            assert len(genders) == 1, f"Group has mixed genders: {genders}"

    def test_all_male_one_gender(self):
        people = make_people(8, 0)
        groups = sort_groups(people, START, END, 4, "mixed", gender_mode="isolated")
        assert sum(len(g) for g in groups) == 8
        for group in groups:
            for p in group:
                assert p.gender == "M"

    def test_gender_isolated_with_age_isolated(self):
        # Mix of ages across two sub-ranges, split by gender
        people = []
        for i in range(6):
            dob = date(2011, 7 + (i % 5), 1)  # sub-range 1
            people.append(person(f"M_{i}", dob, "M"))
        for i in range(4):
            dob = date(2012, 7 + (i % 5), 1)  # sub-range 2
            people.append(person(f"F_{i}", dob, "F"))
        groups = sort_groups(people, START, END, 4, "isolated", gender_mode="isolated")
        assert sum(len(g) for g in groups) == 10
        for group in groups:
            if not group:
                continue
            genders = {p.gender for p in group}
            assert len(genders) == 1


# ---------------------------------------------------------------------------
# sort_groups — gender_mode="mixed"
# ---------------------------------------------------------------------------

class TestGenderMixed:
    def test_total_people_preserved(self):
        people = make_people(8, 4)
        groups = sort_groups(people, START, END, 4, "mixed", gender_mode="mixed")
        assert sum(len(g) for g in groups) == 12

    def test_correct_number_of_groups(self):
        people = make_people(6, 6)
        groups = sort_groups(people, START, END, 3, "mixed", gender_mode="mixed")
        assert len(groups) == 3

    def test_gender_spread_across_groups(self):
        # With equal M/F, every group should have both
        people = make_people(6, 6)
        groups = sort_groups(people, START, END, 3, "mixed", gender_mode="mixed")
        for group in groups:
            genders = {p.gender for p in group}
            assert "M" in genders and "F" in genders

    def test_none_gender_mode_ignores_gender(self):
        people = make_people(6, 6)
        groups = sort_groups(people, START, END, 3, "mixed", gender_mode=None)
        assert sum(len(g) for g in groups) == 12
