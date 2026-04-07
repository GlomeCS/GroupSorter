"""School year date calculations and age group definitions."""

from dataclasses import dataclass
from datetime import date


@dataclass
class AgeGroup:
    label: str          # e.g. "P1 & P2 (Foundation Stage)"
    ages: str           # e.g. "4–6"
    start_date: date
    end_date: date

    def __str__(self) -> str:
        return (
            f"{self.label} (ages {self.ages}): "
            f"{_fmt(self.start_date)} – {_fmt(self.end_date)}"
        )


def _fmt(d: date) -> str:
    return d.strftime("%-d %b %Y") if hasattr(date, "strftime") else str(d)


# Fixed age bands: (label, ages_str, older_age, younger_age)
# Birth range = July 1 (school_year_start - older_age) to June 30 (school_year_start - younger_age)
_BANDS = [
    ("P1 & P2 (Foundation Stage)", "4–6",  6,  4),
    ("P3 & P4 (Key Stage 1)",      "6–8",  8,  6),
    ("P5 & P6 (Key Stage 2)",      "8–10", 10, 8),
    ("P7 & Year 8 (Transition)",   "10–12",12, 10),
    ("Year 9 & Year 10 (Key Stage 3)", "12–14", 14, 12),
    ("Year 11, Year 12 & Year 13 (Key Stage 4 & Post-16)", "14–17", 17, 14),
]


def current_school_year_start(today: date | None = None) -> int:
    """Return the start year of the current school year (July 1 cutoff).

    e.g. called in March 2026 → returns 2025 (school year 2025-26).
    """
    if today is None:
        today = date.today()
    if today.month >= 7:
        return today.year
    return today.year - 1


def suggested_age_groups(school_year_start: int | None = None) -> list[AgeGroup]:
    """Return all 6 standard age groups for the given (or current) school year."""
    if school_year_start is None:
        school_year_start = current_school_year_start()
    groups = []
    for label, ages, older, younger in _BANDS:
        start = date(school_year_start - older, 7, 1)
        end = date(school_year_start - younger, 6, 30)
        groups.append(AgeGroup(label=label, ages=ages, start_date=start, end_date=end))
    return groups


def sub_ranges(start_date: date, end_date: date) -> list[tuple[date, date]]:
    """Split a date range into 1-school-year sub-ranges on July 1 boundaries.

    e.g. July 1 2011 – June 30 2013 → [(2011-07-01, 2012-06-30), (2012-07-01, 2013-06-30)]
    """
    ranges: list[tuple[date, date]] = []
    current_start = start_date
    while current_start < end_date:
        # Next July 1 after current_start (or same day if already July 1)
        next_boundary = date(current_start.year + 1, 7, 1)
        sub_end = date(next_boundary.year, 6, 30)
        if sub_end >= end_date:
            sub_end = end_date
        ranges.append((current_start, sub_end))
        current_start = next_boundary
        if current_start > end_date:
            break
    return ranges
