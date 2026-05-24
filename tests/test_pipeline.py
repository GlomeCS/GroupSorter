"""Integration tests for the run_sort pipeline."""

from datetime import date

from groupsorter.domain import Person
from groupsorter.sorter import SortResult, run_sort

START = date(2011, 7, 1)
END = date(2013, 6, 30)


def person(name: str, dob: date | None, gender: str | None = None) -> Person:
    raw_dob = str(dob) if dob else "bad"
    return Person(name=name, dob=dob, raw_dob=raw_dob, gender=gender)


def make_people(n_r1: int, n_r2: int, gender: str | None = None) -> list[Person]:
    people = []
    for i in range(n_r1):
        people.append(person(f"R1_{i}", date(2011, 7 + (i % 5), 1), gender))
    for i in range(n_r2):
        people.append(person(f"R2_{i}", date(2012, 7 + (i % 5), 1), gender))
    return people


class TestRunSortReturnsResult:
    def test_returns_sort_result(self):
        people = make_people(4, 4)
        result = run_sort(people, START, END, 2, "mixed", None)
        assert isinstance(result, SortResult)

    def test_total_people_preserved(self):
        people = make_people(5, 5)
        result = run_sort(people, START, END, 2, "mixed", None)
        total = (
            sum(len(g) for g in result.groups)
            + len(result.dob_anomalies)
            + len(result.gender_anomalies)
        )
        assert total == 10


class TestDobAnomalyExclusion:
    def test_dob_anomalies_excluded_from_groups(self):
        valid = make_people(4, 4)
        anomalous = [person("OldPerson", date(2009, 1, 1))]
        result = run_sort(valid + anomalous, START, END, 2, "mixed", None)
        assert sum(len(g) for g in result.groups) == 8

    def test_dob_anomalies_returned(self):
        valid = make_people(3, 3)
        anomalous = [person("OldPerson", date(2009, 1, 1))]
        result = run_sort(valid + anomalous, START, END, 2, "mixed", None)
        assert len(result.dob_anomalies) == 1
        assert result.dob_anomalies[0].name == "OldPerson"

    def test_missing_dob_is_anomaly(self):
        valid = make_people(4, 4)
        no_dob = [person("NoDOB", None)]
        result = run_sort(valid + no_dob, START, END, 2, "mixed", None)
        assert any(p.name == "NoDOB" for p in result.dob_anomalies)

    def test_no_anomalies(self):
        people = make_people(4, 4)
        result = run_sort(people, START, END, 2, "mixed", None)
        assert result.dob_anomalies == []


class TestGenderAnomalyExclusion:
    def test_gender_anomalies_excluded_from_groups(self):
        valid = [person(f"P{i}", date(2012, 1, i % 28 + 1), "M") for i in range(6)]
        no_gender = [person("NoG", date(2012, 3, 1), None)]
        result = run_sort(valid + no_gender, START, END, 2, "mixed", "mixed")
        assert sum(len(g) for g in result.groups) == 6

    def test_gender_anomalies_returned(self):
        valid = [person(f"P{i}", date(2012, 1, i % 28 + 1), "M") for i in range(4)]
        no_gender = [person("NoG", date(2012, 3, 1), None)]
        result = run_sort(valid + no_gender, START, END, 2, "mixed", "mixed")
        assert len(result.gender_anomalies) == 1
        assert result.gender_anomalies[0].name == "NoG"

    def test_no_gender_mode_ignores_missing_gender(self):
        people = [person(f"P{i}", date(2012, 1, i % 28 + 1), None) for i in range(6)]
        result = run_sort(people, START, END, 2, "mixed", None)
        assert result.gender_anomalies == []
        assert sum(len(g) for g in result.groups) == 6


class TestFellBack:
    def test_fell_back_false_for_mixed_mode(self):
        people = make_people(4, 4)
        result = run_sort(people, START, END, 2, "mixed", None)
        assert result.fell_back is False

    def test_fell_back_false_when_enough_groups(self):
        people = make_people(4, 4)
        result = run_sort(people, START, END, 2, "isolated", None)
        assert result.fell_back is False

    def test_fell_back_true_when_more_sub_ranges_than_groups(self):
        people = make_people(4, 4)  # 2 non-empty sub-ranges
        result = run_sort(people, START, END, 1, "isolated", None)
        assert result.fell_back is True

    def test_fell_back_false_single_occupied_band(self):
        # All people in one sub-range; empty bands must not count toward fallback threshold
        people = make_people(4, 0)
        result = run_sort(people, START, END, 2, "isolated", None)
        assert result.fell_back is False

    def test_fell_back_true_compound_gender_isolated(self):
        # Males span both sub-ranges but only 1 male group allocated → falls back
        males = make_people(2, 2, "M")   # 2 in sub-range 1, 2 in sub-range 2
        females = make_people(4, 0, "F") # all in sub-range 1
        result = run_sort(males + females, START, END, 2, "isolated", "isolated")
        assert result.fell_back is True

    def test_fell_back_false_compound_gender_isolated(self):
        # Each gender confined to one sub-range; 1 group each → no fallback
        males = [person(f"M{i}", date(2011, 7, i + 1), "M") for i in range(4)]
        females = [person(f"F{i}", date(2012, 7, i + 1), "F") for i in range(4)]
        result = run_sort(males + females, START, END, 2, "isolated", "isolated")
        assert result.fell_back is False


class TestGenderAlloc:
    def test_none_when_gender_mode_is_none(self):
        people = make_people(4, 4)
        result = run_sort(people, START, END, 4, "mixed", None)
        assert result.gender_alloc is None

    def test_none_when_gender_mode_is_mixed(self):
        people = [person(f"M{i}", date(2012, 1, i % 28 + 1), "M") for i in range(4)]
        people += [person(f"F{i}", date(2012, 2, i % 28 + 1), "F") for i in range(4)]
        result = run_sort(people, START, END, 4, "mixed", "mixed")
        assert result.gender_alloc is None

    def test_gender_alloc_proportional_for_isolated(self):
        males = [person(f"M{i}", date(2012, 1, i % 28 + 1), "M") for i in range(6)]
        females = [person(f"F{i}", date(2012, 2, i % 28 + 1), "F") for i in range(6)]
        result = run_sort(males + females, START, END, 4, "mixed", "isolated")
        assert result.gender_alloc is not None
        male_g, female_g = result.gender_alloc
        assert male_g + female_g == 4
        assert male_g == female_g == 2

    def test_gender_alloc_sums_to_num_groups(self):
        males = [person(f"M{i}", date(2012, 1, i % 28 + 1), "M") for i in range(9)]
        females = [person(f"F{i}", date(2012, 2, i % 28 + 1), "F") for i in range(3)]
        result = run_sort(males + females, START, END, 4, "mixed", "isolated")
        assert result.gender_alloc is not None
        assert sum(result.gender_alloc) == 4

    def test_gender_alloc_all_male(self):
        males = make_people(4, 4, "M")
        result = run_sort(males, START, END, 4, "mixed", "isolated")
        assert result.gender_alloc == (4, 0)

    def test_gender_alloc_all_female(self):
        females = make_people(4, 4, "F")
        result = run_sort(females, START, END, 4, "mixed", "isolated")
        assert result.gender_alloc == (0, 4)


class TestTotalPreservation:
    def test_groups_plus_anomalies_equals_input(self):
        valid = make_people(6, 6)
        dob_bad = [person("OldP", date(2005, 1, 1))]
        gen_bad = [person("NoG", date(2012, 3, 1), None)]
        all_people = valid + dob_bad + gen_bad
        result = run_sort(all_people, START, END, 3, "mixed", "mixed")
        total = (
            sum(len(g) for g in result.groups)
            + len(result.dob_anomalies)
            + len(result.gender_anomalies)
        )
        assert total == len(all_people)
