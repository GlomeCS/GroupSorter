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
) -> list[list[Person]]:
    """Sort people into num_groups groups.

    Only people whose DOB falls within [start_date, end_date] are sorted.
    People with a missing DOB or outside the range are excluded (run anomaly
    check separately).

    mode="mixed"    — each group receives an even spread from every sub-range.
    mode="isolated" — each group contains people from only one sub-range.
    """
    if num_groups < 1:
        raise ValueError("num_groups must be at least 1")

    bands = sub_ranges(start_date, end_date)

    # Partition valid people into sub-range buckets
    buckets: list[list[Person]] = [[] for _ in bands]
    for person in people:
        if person.dob is None:
            continue
        if not (start_date <= person.dob <= end_date):
            continue
        for i, (band_start, band_end) in enumerate(bands):
            if band_start <= person.dob <= band_end:
                buckets[i].append(person)
                break

    if mode == "mixed":
        return _sort_mixed(buckets, num_groups)
    elif mode == "isolated":
        return _sort_isolated(buckets, num_groups)
    else:
        raise ValueError(f"Unknown mode: {mode!r}. Expected 'mixed' or 'isolated'.")


def _sort_mixed(buckets: list[list[Person]], num_groups: int) -> list[list[Person]]:
    """Distribute people round-robin per bucket so each group gets a mix of all sub-ranges."""
    groups: list[list[Person]] = [[] for _ in range(num_groups)]
    for bucket in buckets:
        for i, person in enumerate(bucket):
            groups[i % num_groups].append(person)
    return groups


def _sort_isolated(buckets: list[list[Person]], num_groups: int) -> list[list[Person]]:
    """Allocate groups proportionally to sub-ranges; each group holds one sub-range only."""
    total = sum(len(b) for b in buckets)
    if total == 0:
        return [[] for _ in range(num_groups)]

    # Proportional allocation — at least 1 group per non-empty bucket
    non_empty = [b for b in buckets if b]
    if len(non_empty) > num_groups:
        # More sub-ranges than groups: collapse smaller buckets into largest
        # (best-effort — put everyone into groups round-robin)
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

    # Pad to num_groups if needed (empty buckets left gaps)
    while len(groups) < num_groups:
        groups.append([])

    return groups[:num_groups]


def _proportional_allocate(counts: list[int], total_slots: int) -> list[int]:
    """Allocate total_slots proportionally among buckets. Non-empty buckets get >= 1."""
    total = sum(counts)
    if total == 0:
        return [0] * len(counts)

    # Compute raw proportional share
    raw = [total_slots * c / total for c in counts]
    floored = [int(r) for r in raw]
    remainder = total_slots - sum(floored)

    # Non-empty buckets must get at least 1
    for i, c in enumerate(counts):
        if c > 0 and floored[i] == 0:
            floored[i] = 1
            remainder -= 1

    # Distribute remaining slots by largest fractional part (largest-remainder method)
    if remainder > 0:
        fractions = [(raw[i] - floored[i], i) for i in range(len(counts))]
        fractions.sort(reverse=True)
        for _, i in fractions[:remainder]:
            floored[i] += 1
    elif remainder < 0:
        # We over-allocated due to the "at least 1" adjustment; trim from largest
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


def format_groups_report(groups: list[list[Person]], mode: str, fell_back: bool = False) -> str:
    if mode == "mixed":
        mode_label = "Mixed (age ranges distributed)"
    elif fell_back:
        mode_label = "Isolated → fell back to Mixed (more sub-ranges than groups)"
    else:
        mode_label = "Isolated (one age range per group)"
    lines = [f"Sort mode: {mode_label}", f"Groups: {len(groups)}", ""]
    for i, group in enumerate(groups, 1):
        lines.append(f"── Group {i} ({len(group)} {'person' if len(group) == 1 else 'people'}) ──")
        if group:
            for person in group:
                dob_str = person.dob.strftime("%d %b %Y") if person.dob else "unknown DOB"
                lines.append(f"  {person.name}  ({dob_str})")
        else:
            lines.append("  (empty)")
        lines.append("")
    return "\n".join(lines)
