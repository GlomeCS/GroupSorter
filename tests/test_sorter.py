"""Tests for group sorting logic."""

from datetime import date

from groupsorter.domain import Person
from groupsorter.sorter import _proportional_allocate, sort_groups


def person(name: str, dob: date) -> Person:
    return Person(name=name, dob=dob)


# 2-year range: two sub-ranges
START_2 = date(2011, 7, 1)
END_2 = date(2013, 6, 30)

# 3-year range
START_3 = date(2008, 7, 1)
END_3 = date(2011, 6, 30)


def make_people_2yr(n_r1: int, n_r2: int) -> list[Person]:
    """Create n_r1 people in range 1 (2011-12) and n_r2 in range 2 (2012-13)."""
    people = []
    for i in range(n_r1):
        people.append(person(f"R1_{i}", date(2011, 7 + (i % 5), 1)))
    for i in range(n_r2):
        people.append(person(f"R2_{i}", date(2012, 7 + (i % 5), 1)))
    return people


class TestMixedMode:
    def test_total_people_preserved(self):
        people = make_people_2yr(10, 8)
        groups = sort_groups(people, START_2, END_2, 4, "mixed")
        assert sum(len(g) for g in groups) == 18

    def test_correct_number_of_groups(self):
        people = make_people_2yr(6, 6)
        groups = sort_groups(people, START_2, END_2, 3, "mixed")
        assert len(groups) == 3

    def test_even_distribution(self):
        people = make_people_2yr(6, 6)
        groups = sort_groups(people, START_2, END_2, 3, "mixed")
        sizes = [len(g) for g in groups]
        assert max(sizes) - min(sizes) <= 1

    def test_uneven_distribution_handled(self):
        # 7 people, 3 groups — can't divide evenly
        people = make_people_2yr(4, 3)
        groups = sort_groups(people, START_2, END_2, 3, "mixed")
        assert sum(len(g) for g in groups) == 7

    def test_more_groups_than_people(self):
        people = make_people_2yr(2, 1)
        groups = sort_groups(people, START_2, END_2, 5, "mixed")
        assert sum(len(g) for g in groups) == 3

    def test_excludes_out_of_range(self):
        people = make_people_2yr(4, 4)
        people.append(person("OutOfRange", date(2014, 1, 1)))
        groups = sort_groups(people, START_2, END_2, 2, "mixed")
        assert sum(len(g) for g in groups) == 8  # out-of-range excluded


class TestIsolatedMode:
    def test_total_people_preserved(self):
        people = make_people_2yr(10, 8)
        groups = sort_groups(people, START_2, END_2, 4, "isolated")
        assert sum(len(g) for g in groups) == 18

    def test_correct_number_of_groups(self):
        people = make_people_2yr(6, 6)
        groups = sort_groups(people, START_2, END_2, 4, "isolated")
        assert len(groups) == 4

    def test_three_sub_ranges(self):
        people = [
            person("A", date(2008, 9, 1)),
            person("B", date(2009, 9, 1)),
            person("C", date(2010, 9, 1)),
            person("D", date(2008, 11, 1)),
            person("E", date(2009, 11, 1)),
            person("F", date(2010, 11, 1)),
        ]
        groups = sort_groups(people, START_3, END_3, 3, "isolated")
        assert sum(len(g) for g in groups) == 6
        assert len(groups) == 3

    def test_groups_contain_single_sub_range(self):
        # 4 groups, 2 sub-ranges → 2 groups per sub-range; each group must be pure
        people = make_people_2yr(6, 6)
        groups = sort_groups(people, START_2, END_2, 4, "isolated")
        r1_start, r1_end = date(2011, 7, 1), date(2012, 6, 30)
        r2_start, r2_end = date(2012, 7, 1), date(2013, 6, 30)
        for group in groups:
            if not group:
                continue
            in_r1 = all(r1_start <= p.dob <= r1_end for p in group)
            in_r2 = all(r2_start <= p.dob <= r2_end for p in group)
            assert in_r1 or in_r2, "Group mixes people from different sub-ranges"



class TestProportionalAllocate:
    def test_equal_split(self):
        result = _proportional_allocate([10, 10], 4)
        assert result == [2, 2]
        assert sum(result) == 4

    def test_unequal_split(self):
        result = _proportional_allocate([20, 10], 3)
        assert sum(result) == 3
        assert result[0] > result[1]

    def test_non_empty_gets_at_least_one(self):
        result = _proportional_allocate([100, 1], 2)
        assert result[1] >= 1
        assert sum(result) == 2

    def test_empty_bucket_gets_zero(self):
        result = _proportional_allocate([10, 0, 10], 4)
        assert result[1] == 0
        assert sum(result) == 4

    def test_three_buckets(self):
        result = _proportional_allocate([9, 9, 9], 6)
        assert result == [2, 2, 2]
