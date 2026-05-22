"""Group sorting: Mixed and Isolated modes, supporting 1 or more age sub-ranges."""

from dataclasses import dataclass
from datetime import date

from .anomaly import find_anomalies, find_gender_anomalies
from .date_utils import sub_ranges
from .domain import Person
from .reporting import format_groups_report

__all__ = [
    "SortResult",
    "run_sort",
    "sort_groups",
    "format_groups_report",
]


@dataclass
class SortResult:
    groups: list[list[Person]]
    dob_anomalies: list[Person]
    gender_anomalies: list[Person]
    fell_back: bool
    gender_alloc: tuple[int, int] | None  # (male_groups, female_groups) or None


def run_sort(
    people: list[Person],
    start: date,
    end: date,
    num_groups: int,
    age_mode: str,
    gender_mode: str | None,
) -> SortResult:
    """Run the full sort pipeline: anomaly exclusion → sort → structured result.

    Callers pass the raw people list; this function excludes anomalies internally
    and returns them alongside the sorted groups.
    """
    dob_anomalies = find_anomalies(people, start, end)
    anomaly_ids = {id(p) for p in dob_anomalies}
    valid = [p for p in people if id(p) not in anomaly_ids]

    gender_anomalies: list[Person] = []
    gender_alloc: tuple[int, int] | None = None
    if gender_mode is not None:
        gender_anomalies = find_gender_anomalies(valid)
        gender_anomaly_ids = {id(p) for p in gender_anomalies}
        valid = [p for p in valid if id(p) not in gender_anomaly_ids]

    if gender_mode == "isolated":
        alloc = _gender_allocation(valid, num_groups, start, end)
        gender_alloc = alloc

    fell_back = False
    if age_mode == "isolated":
        if gender_mode == "isolated" and gender_alloc is not None:
            male_valid = [p for p in valid if p.gender == "M"]
            female_valid = [p for p in valid if p.gender == "F"]
            male_g, female_g = gender_alloc
            fell_back = (
                (male_g > 0 and _isolated_would_fall_back(male_valid, start, end, male_g))
                or (female_g > 0 and _isolated_would_fall_back(female_valid, start, end, female_g))
            )
        else:
            fell_back = _isolated_would_fall_back(valid, start, end, num_groups)

    groups = sort_groups(valid, start, end, num_groups, age_mode, gender_mode)

    return SortResult(
        groups=groups,
        dob_anomalies=dob_anomalies,
        gender_anomalies=gender_anomalies,
        fell_back=fell_back,
        gender_alloc=gender_alloc,
    )


def sort_groups(
    people: list[Person],
    start_date: date,
    end_date: date,
    num_groups: int,
    mode: str,  # "mixed" or "isolated"
    gender_mode: str | None = None,  # "mixed", "isolated", or None
) -> list[list[Person]]:
    """Sort people into num_groups groups.

    Only people whose DOB falls within [start_date, end_date] are sorted.
    People with a missing DOB, out-of-range DOB, or (when gender_mode is set)
    missing gender should be excluded by the caller before this function.

    mode="mixed"    — each group receives an even spread from every age sub-range.
    mode="isolated" — each group contains people from only one age sub-range.

    gender_mode="mixed"    — M and F are interleaved within each age bucket before
                             distribution, so each group gets a spread of both.
    gender_mode="isolated" — groups are first split proportionally by gender, then
                             the age mode is applied within each gender's allocation.
                             Guarantee: no group will contain more than one gender.
    gender_mode=None       — gender is ignored entirely.
    """
    if num_groups < 1:
        raise ValueError("num_groups must be at least 1")
    if mode not in ("mixed", "isolated"):
        raise ValueError(f"Unknown mode: {mode!r}. Expected 'mixed' or 'isolated'.")

    bands = sub_ranges(start_date, end_date)
    if not bands:
        bands = [(start_date, end_date)]

    def make_buckets(persons: list[Person]) -> list[list[Person]]:
        buckets: list[list[Person]] = [[] for _ in bands]
        for person in persons:
            if person.dob is None:
                continue
            if not (start_date <= person.dob <= end_date):
                continue
            for i, (band_start, band_end) in enumerate(bands):
                if band_start <= person.dob <= band_end:
                    buckets[i].append(person)
                    break
        return buckets

    if gender_mode in ("mixed", "isolated"):
        invalid_gender = [
            p for p in people
            if p.dob is not None
            and start_date <= p.dob <= end_date
            and p.gender not in ("M", "F")
        ]
        if invalid_gender:
            raise ValueError(
                f"sort_groups received {len(invalid_gender)} person(s) with gender not "
                "'M' or 'F'. Exclude gender anomalies before calling."
            )

    if gender_mode == "isolated":
        male = [p for p in people if p.gender == "M"]
        female = [p for p in people if p.gender == "F"]

        male_valid_count = sum(
            1 for p in male if p.dob is not None and start_date <= p.dob <= end_date
        )
        female_valid_count = sum(
            1 for p in female if p.dob is not None and start_date <= p.dob <= end_date
        )
        allocs = _proportional_allocate([male_valid_count, female_valid_count], num_groups)
        male_groups_count, female_groups_count = allocs[0], allocs[1]

        groups: list[list[Person]] = []

        if male_groups_count > 0:
            male_buckets = make_buckets(male)
            if mode == "mixed":
                groups.extend(_sort_mixed(male_buckets, male_groups_count))
            else:
                groups.extend(_sort_isolated(male_buckets, male_groups_count))
        if female_groups_count > 0:
            female_buckets = make_buckets(female)
            if mode == "mixed":
                groups.extend(_sort_mixed(female_buckets, female_groups_count))
            else:
                groups.extend(_sort_isolated(female_buckets, female_groups_count))

        while len(groups) < num_groups:
            groups.append([])
        return groups[:num_groups]

    else:
        buckets = make_buckets(people)
        if gender_mode == "mixed":
            buckets = [_interleave_genders(b) for b in buckets]

        if mode == "mixed":
            return _sort_mixed(buckets, num_groups)
        else:
            return _sort_isolated(buckets, num_groups)


def _interleave_genders(bucket: list[Person]) -> list[Person]:
    """Alternate M and F within a bucket so gender is spread evenly across groups."""
    males = [p for p in bucket if p.gender == "M"]
    females = [p for p in bucket if p.gender == "F"]
    if len(males) + len(females) != len(bucket):
        raise ValueError(
            f"_interleave_genders received {len(bucket) - len(males) - len(females)} "
            "person(s) with gender not 'M' or 'F'. Filter gender anomalies before calling."
        )
    result: list[Person] = []
    for i in range(max(len(males), len(females))):
        if i < len(males):
            result.append(males[i])
        if i < len(females):
            result.append(females[i])
    return result


def _sort_mixed(buckets: list[list[Person]], num_groups: int) -> list[list[Person]]:
    """Distribute people round-robin across all buckets so each group gets a mix of sub-ranges."""
    groups: list[list[Person]] = [[] for _ in range(num_groups)]
    cursor = 0
    for bucket in buckets:
        for person in bucket:
            groups[cursor % num_groups].append(person)
            cursor += 1
    return groups


def _sort_isolated(buckets: list[list[Person]], num_groups: int) -> list[list[Person]]:
    """Allocate groups proportionally to sub-ranges; each group holds one sub-range only."""
    total = sum(len(b) for b in buckets)
    if total == 0:
        return [[] for _ in range(num_groups)]

    non_empty = [b for b in buckets if b]
    if len(non_empty) > num_groups:
        # More sub-ranges than groups: fall back to mixed
        return _sort_mixed(buckets, num_groups)

    allocations = _proportional_allocate(
        counts=[len(b) for b in buckets],
        total_slots=num_groups,
    )

    groups: list[list[Person]] = []
    for bucket, alloc in zip(buckets, allocations, strict=True):
        if alloc == 0:
            continue
        sub_groups: list[list[Person]] = [[] for _ in range(alloc)]
        for j, person in enumerate(bucket):
            sub_groups[j % alloc].append(person)
        groups.extend(sub_groups)

    while len(groups) < num_groups:
        groups.append([])

    return groups[:num_groups]


def _proportional_allocate(counts: list[int], total_slots: int) -> list[int]:
    """Allocate total_slots proportionally among buckets. Non-empty buckets get >= 1."""
    total = sum(counts)
    if total == 0:
        return [0] * len(counts)

    raw = [total_slots * c / total for c in counts]
    floored = [int(r) for r in raw]
    remainder = total_slots - sum(floored)

    for i, c in enumerate(counts):
        if c > 0 and floored[i] == 0:
            floored[i] = 1
            remainder -= 1

    if remainder > 0:
        fractions = [(raw[i] - floored[i], i) for i in range(len(counts))]
        fractions.sort(reverse=True)
        for _, i in fractions[:remainder]:
            floored[i] += 1
    elif remainder < 0:
        for _ in range(-remainder):
            over_alloc = [i for i in range(len(floored)) if floored[i] > 1]
            if over_alloc:
                idx = max(over_alloc, key=lambda i: floored[i])
            else:
                # Every non-empty bucket was bumped to 1 but slots are exhausted;
                # take back from the bucket with the smallest proportional share.
                bumped = [i for i in range(len(floored)) if floored[i] > 0]
                idx = min(bumped, key=lambda i: raw[i])
            floored[idx] -= 1

    return floored


def _isolated_would_fall_back(
    people: list[Person],
    start_date: date,
    end_date: date,
    num_groups: int,
) -> bool:
    bands = sub_ranges(start_date, end_date)
    non_empty_count = sum(
        1 for band_start, band_end in bands
        if any(band_start <= p.dob <= band_end for p in people if p.dob is not None)
    )
    return non_empty_count > num_groups


def _gender_allocation(
    people: list[Person],
    num_groups: int,
    start_date: date,
    end_date: date,
) -> tuple[int, int]:
    male_count = sum(
        1 for p in people
        if p.gender == "M" and p.dob is not None and start_date <= p.dob <= end_date
    )
    female_count = sum(
        1 for p in people
        if p.gender == "F" and p.dob is not None and start_date <= p.dob <= end_date
    )
    allocs = _proportional_allocate([male_count, female_count], num_groups)
    return allocs[0], allocs[1]
