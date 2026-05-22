"""Group sorting: Mixed and Isolated modes, supporting 1 or more age sub-ranges."""

from datetime import date

from .anomaly import Person
from .date_utils import sub_ranges


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
        elif mode == "isolated":
            return _sort_isolated(buckets, num_groups)
        else:
            raise ValueError(f"Unknown mode: {mode!r}. Expected 'mixed' or 'isolated'.")


def _interleave_genders(bucket: list[Person]) -> list[Person]:
    """Alternate M and F within a bucket so gender is spread evenly across groups."""
    males = [p for p in bucket if p.gender == "M"]
    females = [p for p in bucket if p.gender == "F"]
    other = [p for p in bucket if p.gender not in ("M", "F")]
    result: list[Person] = []
    for i in range(max(len(males), len(females))):
        if i < len(males):
            result.append(males[i])
        if i < len(females):
            result.append(females[i])
    result.extend(other)
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
            idx = max(
                (i for i in range(len(floored)) if floored[i] > 1),
                key=lambda i: floored[i],
                default=0,
            )
            floored[idx] -= 1

    return floored


def isolated_would_fall_back(
    people: list[Person],
    start_date: date,
    end_date: date,
    num_groups: int,
) -> bool:
    """Return True if isolated mode would fall back to mixed for the given inputs.

    Isolated mode falls back when there are more non-empty sub-ranges than groups.
    """
    bands = sub_ranges(start_date, end_date)
    non_empty_count = sum(
        1 for band_start, band_end in bands
        if any(band_start <= p.dob <= band_end for p in people if p.dob is not None)
    )
    return non_empty_count > num_groups


def gender_allocation(people: list[Person], num_groups: int) -> tuple[int, int]:
    """Return (male_groups, female_groups) for isolated gender mode."""
    male_count = sum(1 for p in people if p.gender == "M")
    female_count = sum(1 for p in people if p.gender == "F")
    allocs = _proportional_allocate([male_count, female_count], num_groups)
    return allocs[0], allocs[1]


def format_groups_report(
    groups: list[list[Person]],
    mode: str,
    fell_back: bool = False,
    gender_mode: str | None = None,
) -> str:
    if mode == "mixed":
        age_label = "Mixed (age ranges distributed)"
    elif fell_back:
        age_label = "Isolated → fell back to Mixed (more sub-ranges than groups)"
    else:
        age_label = "Isolated (one age range per group)"

    lines = [f"Age sort mode: {age_label}"]

    if gender_mode == "mixed":
        lines.append("Gender sort mode: Mixed (gender spread across groups)")
    elif gender_mode == "isolated":
        lines.append("Gender sort mode: Isolated (one gender per group)")

    lines += [f"Groups: {len(groups)}", ""]

    has_gender = any(p.gender is not None for group in groups for p in group)

    for i, group in enumerate(groups, 1):
        lines.append(f"── Group {i} ({len(group)} {'person' if len(group) == 1 else 'people'}) ──")
        if group:
            if has_gender:
                m_count = sum(1 for p in group if p.gender == "M")
                f_count = sum(1 for p in group if p.gender == "F")
                lines.append(f"  [{m_count}M / {f_count}F]")
            for person in group:
                dob_str = person.dob.strftime("%d %b %Y") if person.dob else "unknown DOB"
                gender_str = f" [{person.gender}]" if person.gender else ""
                lines.append(f"  {person.name}  ({dob_str}){gender_str}")
        else:
            lines.append("  (empty)")
        lines.append("")
    return "\n".join(lines)
